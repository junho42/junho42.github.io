/* 포트폴리오 동작 — 의존성 없음.
   JS가 없어도 그리드와 게시물은 정적 HTML로 전부 보인다.
   여기서 하는 일은 메이슨리 배치, 스크롤에 따라 카드 풀기, 맨 위로
   버튼, 이미지 확대다.
   카드는 모두 이미 HTML에 들어 있고, 여기서는 숨김만 걷어낸다 —
   네트워크 요청도, 가져올 데이터도 없다. */
(function () {
  'use strict';

  // 이 클래스가 붙은 뒤에만 CSS가 초과 카드를 숨긴다.
  document.documentElement.classList.add('js');

  // 1) 메이슨리 — 카드 높이를 1px 행 span으로 바꿔 열을 틈 없이 채운다.
  //    카드 높이는 img의 width/height 속성에서 바로 나오므로 이미지가
  //    실리기를 기다릴 필요가 없다.
  var grid = document.querySelector('.grid');

  function applyMasonry() {
    if (!grid) return;
    var gap = parseFloat(getComputedStyle(grid).columnGap) || 0;
    var cards = grid.querySelectorAll('.card');
    var heights = [];
    var i;
    // 읽기를 먼저 몰아서 하고 쓰기를 뒤로 미뤄, 카드마다 레이아웃을
    // 다시 계산하게 만드는 스래싱을 피한다.
    for (i = 0; i < cards.length; i++) {
      heights.push(cards[i].getBoundingClientRect().height);
    }
    grid.classList.add('is-masonry');
    for (i = 0; i < cards.length; i++) {
      // 숨은 카드는 높이가 0이다. 풀릴 때 다시 계산한다.
      if (heights[i]) {
        cards[i].style.gridRowEnd = 'span ' + Math.ceil(heights[i] + gap);
      }
    }
  }

  applyMasonry();

  // 열 폭이 바뀌면 카드 높이도 바뀌므로 다시 계산한다.
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(applyMasonry, 150);
  });

  // 2) 스크롤이 바닥에 가까워지면 한 묶음씩 더 보여준다.
  var BATCH = 12;
  var LOOKAHEAD = 600; // 바닥에 닿기 전에 미리 풀어 빈 화면을 안 만든다

  document.querySelectorAll('.category').forEach(function (section) {
    var button = section.querySelector('.more');

    // 버튼은 IntersectionObserver가 없는 브라우저의 폴백으로 남긴다.
    if (button) {
      button.addEventListener('click', function () {
        section.classList.add('is-open');
        applyMasonry();
      });
    }

    if (!('IntersectionObserver' in window)) return;
    if (!section.querySelector('.card.extra')) return;

    // 스크롤로 자동 확장되므로 버튼은 감춘다.
    if (button) button.hidden = true;

    var sentinel = document.createElement('div');
    sentinel.setAttribute('aria-hidden', 'true');
    section.appendChild(sentinel);

    var observer = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) step();
    }, { rootMargin: LOOKAHEAD + 'px 0px' });

    function step() {
      var hidden = section.querySelectorAll('.card.extra:not(.shown)');
      if (!hidden.length) {
        observer.disconnect();
        sentinel.remove();
        return;
      }
      for (var i = 0; i < BATCH && i < hidden.length; i++) {
        hidden[i].classList.add('shown');
      }
      // 방금 풀린 카드는 높이가 0이었으므로 span이 없다. 지금 계산한다.
      applyMasonry();
      // 카드를 풀어도 sentinel이 여전히 화면 안에 있으면 옵저버는 다시
      // 울리지 않는다(교차 상태가 안 바뀌므로). 다음 프레임에 직접 확인한다.
      requestAnimationFrame(function () {
        if (!sentinel.parentNode) return;
        if (sentinel.getBoundingClientRect().top < window.innerHeight + LOOKAHEAD) {
          step();
        }
      });
    }

    observer.observe(sentinel);
  });

  // 3) 맨 위로 — 조금 내려간 뒤부터 보인다.
  var toTop = document.querySelector('.to-top');
  if (toTop) {
    var SHOW_AFTER = 300;
    var ticking = false;

    function syncToTop() {
      ticking = false;
      var y = window.pageYOffset || document.documentElement.scrollTop;
      toTop.classList.toggle('is-visible', y > SHOW_AFTER);
    }

    window.addEventListener('scroll', function () {
      // 스크롤 이벤트마다 클래스를 만지지 않고 프레임당 한 번만 정리한다.
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(syncToTop);
      }
    }, { passive: true });

    syncToTop();
  }

  // 4) 이미지 확대
  var zoomable = Array.prototype.slice.call(document.querySelectorAll('.shot img[data-zoom]'));
  if (!zoomable.length) return;

  var overlay = null;
  var picture = null;
  var current = 0;

  function show(index) {
    current = (index + zoomable.length) % zoomable.length;
    var source = zoomable[current];
    picture.src = source.getAttribute('data-zoom');
    picture.alt = source.alt || '';
  }

  function close() {
    if (!overlay) return;
    overlay.remove();
    overlay = null;
    document.body.classList.remove('lb-open');
    document.removeEventListener('keydown', onKey);
    zoomable[current].focus({ preventScroll: true });
  }

  function onKey(event) {
    if (event.key === 'Escape') close();
    else if (event.key === 'ArrowRight') show(current + 1);
    else if (event.key === 'ArrowLeft') show(current - 1);
  }

  function open(index) {
    // 이미 열려 있는데 다시 열면(이미지에 포커스가 남은 채 Enter/Space를
    // 또 누르는 경우) 첫 오버레이는 참조를 잃고 DOM에 고아로 남고,
    // 두 번째 오버레이를 닫을 때 overlay = null이 되어 close()가
    // 조용히 아무것도 안 한다 — 페이지가 죽은 검은 막 뒤에 갇힌다.
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.className = 'lightbox';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');

    picture = document.createElement('img');
    overlay.appendChild(picture);

    var closeButton = null;
    [['lb-close', '✕', close],
     ['lb-prev', '‹', function () { show(current - 1); }],
     ['lb-next', '›', function () { show(current + 1); }]
    ].forEach(function (spec) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = spec[0];
      button.textContent = spec[1];
      button.addEventListener('click', function (event) {
        event.stopPropagation();
        spec[2]();
      });
      overlay.appendChild(button);
      if (spec[0] === 'lb-close') closeButton = button;
    });

    overlay.addEventListener('click', close);
    document.body.appendChild(overlay);
    document.body.classList.add('lb-open');
    document.addEventListener('keydown', onKey);
    show(index);
    // 포커스를 오버레이 안으로 옮긴다. 옮기지 않으면 이미지가 계속
    // 포커스를 쥐고 있어(tabIndex = 0) Enter/Space가 open()을 또
    // 부르는 재진입 경로가 된다.
    if (closeButton) closeButton.focus();
  }

  zoomable.forEach(function (image, index) {
    image.tabIndex = 0;
    image.addEventListener('click', function () { open(index); });
    image.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open(index);
      }
    });
  });
})();
