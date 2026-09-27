# SDD ledger — plan: docs/superpowers/plans/2026-09-27-colorist-portfolio.md

Spec: docs/superpowers/specs/2026-09-27-colorist-portfolio-design.md (읽음, 도달 가능)
Worktree: .claude/worktrees/portfolio (branch `portfolio`, base 693f96b)
Baseline: `bundle exec jekyll build` 에러 없음, 파이썬 테스트 0개(정상 — 아직 없음)

## Pre-flight 충돌 스캔

### 파일·인터페이스를 공유하는 태스크 쌍

| 쌍 | 생산 → 소비 | 결과 |
|---|---|---|
| T1 → T9, T11 | `portfolio/site.config.json` → 렌더러·빌드 CLI가 읽음 | 일치. 키 이름(siteName·tagline·siteUrl·email·instagram·about·contactNote·gridPageSize·noindex·ogImage)이 T1 파일과 T9 사용처에서 동일 |
| T1 → T12 | `portfolio/README.md` (T1은 lab 설명 유지, T12가 작가용으로 교체) | 일치. T1이 파일을 지우지 않고 T12가 전체 교체하므로 중간 상태에 구멍 없음 |
| T1 → T12 | `_config.yml` exclude(templates·tools·upload) → T12 Step 5가 `_site` 부재를 검증 | 일치 |
| T2 → T6 | `strip_order_prefix`·`natural_key`·`dedupe_slug` | 일치. 시그니처·반환형 동일 |
| T2 → T8 | `natural_key` (sort_works의 2차 키) | 일치 |
| T3 → T6 | `read_text`·`body_to_html` | 일치 |
| T3 → T9 | `body_to_html` (About/Contact 본문) | 일치. T9가 `from textfile import body_to_html` |
| T4 → T6 | `parse_video_url` | 일치. `None` 반환 조건(주소 아님)을 T6이 링크 실패 경고로 처리 |
| T5 → T11 | `git_added_at` | 일치. T6은 `date`를 채우지 않고(`None` 기본값) T11 `build()`가 채운다 — 역할 분리 명확 |
| T6 → T8 | `Category`·`Work` 데이터클래스 | 일치. T8이 `from scanner import Category, Work` |
| T7 → T8 | `make_cover`·`make_gallery`·`needs_rebuild`·`image_size`·`fetch_youtube_cover`·`COVER_WIDTH`·`GALLERY_WIDTH` | 일치(계획 작성 시 자체 검토에서 `image_size` 누락을 고친 뒤) |
| T8 → T9 | manifest dict 스키마 | 일치. T9가 읽는 키(url·title·slug·date·cover.src/w/h·video.kind/embed/url·images[].src/w/h·body, category.title/slug/works)를 T8이 모두 생산 |
| T8 → T9 | 게시물 출력 경로 | 일치. T8의 `url = works/<category.slug>/<work.slug>/` 와 T9의 쓰기 경로 `works/<slug>/<slug>/index.html` 동일 |
| T9 → T10 | CSS 클래스·`data-more`·`data-zoom` | 일치. T10 Interfaces에 T9이 찍는 선택자 전체를 명시함. `.js` 게이트(JS가 html에 추가 → CSS가 `.js .card.extra`로 숨김)도 양쪽 합치 |
| T9 → T11 | `render_site -> (list[Path], list[str])` | 일치. T11 `build()`가 같은 형태로 받음 |
| T9 → T11 | 생성 페이지 목록 | 일치. `_collect_pages`가 index/about/contact + `works/**/index.html`을 찾고 T9이 정확히 그 경로에 쓴다 |
| T11 → T12 | `build.py` CLI 인자(`--root`·`--check`) | 일치. 워크플로는 인자 없이 호출(기본 root가 `portfolio/`) |

### 태스크별 자기 정합성

| 태스크 | 확인 내용 | 결과 |
|---|---|---|
| T1 | git mv 후 지우는 경로가 실제로 존재하는가 / 검증 명령이 그 상태를 맞게 검사하는가 | 일치 |
| T2 | 테스트가 요구하는 동작이 구현 정규식과 맞는가(`2026웨딩스냅`은 접두사 아님, 혼합 타입 정렬 예외 없음) | 일치. `re.split` 캡처가 짝/홀 인덱스 타입을 고정해 비교 오류 없음 |
| T3 | 인코딩 폴백 순서가 테스트 기대와 맞는가 | 일치. UTF-8 먼저여야 CP949 오판이 안 생긴다는 점이 주석과 테스트에 함께 있음 |
| T4 | 7개 테스트가 구현 분기를 모두 덮는가 | 일치 |
| T5 | git 없는 환경·이력 없는 환경 모두 예외 없이 현재 시각으로 떨어지는가 | 일치 |
| T6 | 13개 테스트 각각이 구현의 실제 정렬·필터 결과와 맞는가 | 일치. 커버 선택 두 테스트(`cover.*` 있음/없음)의 갤러리 잔존 여부가 구현과 일치 |
| T7 | 반올림 결과가 테스트 기대치와 맞는가(600→338, 1600→1067) | 일치 |
| T8 | 정렬 키가 `date=None`을 만나도 비교 오류를 내지 않는가 | 일치. `(w.date is not None, w.date)` 튜플이 None 비교를 차단 |
| T9 | **테스트와 구현이 어긋남 — 아래 Ruling 참조** | **불일치 1건** |
| T10 | CSS 선택자가 T9 마크업과 맞는가 / 축소모션 대응 | 일치. `data-more` 속성은 테스트 훅으로만 쓰이고 JS는 읽지 않음 — 무해 |
| T11 | 6+6개 테스트가 실제 CLI 종료 코드·출력과 맞는가 | 일치 |
| T12 | 검증 명령이 앞선 태스크 산출물 경로와 맞는가 | 일치 |

### Ruling

`Ruling: T9의 test_게시물_OG_태그는_절대주소를_쓴다 가 기대하는 문자열을 퍼센트 인코딩 형태로 고친다 — 구현(_url_path)이 한글 경로를 인코딩하는 것이 맞고 테스트가 틀렸다. og:image는 크롤러·메신저가 읽는 절대 URL이라 non-ASCII를 인코딩해 두는 편이 안전하고, 사이트 내부 링크와 인코딩 규칙을 하나로 유지해야 한다 — 틀렸을 경우의 비용: 카카오톡·슬랙 미리보기에서 커버 이미지가 안 뜰 수 있고, 그때 테스트와 _url_path 호출부 한 곳만 되돌리면 된다.`

## 진행 기록

- Task 1: dispatched (haiku, BASE 6ee9bda) — lab→portfolio 리네임, _config.yml exclude·sitemap 경로, site.config.json
- 브리프 사전 생성: task-1, task-2, task-3

- Task 1: review clean (spec OK, quality Approved, 0 findings). Cannot-verify item(Step 5 Jekyll 빌드)은 컨트롤러가 직접 확인 — portfolio 구조·site.config.json 값 일치 확인 완료, 해소됨.
- Task 1: minor (deferred): 커밋 8933db2의 Co-Authored-By trailer가 빈 줄 없이 제목 줄에 이어붙어 한 줄 커밋이 됐다. 동작 영향 없음, 최종 리뷰에서 triage.
- Task 1: complete (commits 6ee9bda..8933db2, review clean)
- Task 2: dispatched (haiku, BASE 8933db2) — naming.py + conftest.py + test_naming.py
- Task 2: complete (commits 8933db2..1ab0989, review clean — spec OK, quality Approved, 0 findings). 리뷰어가 정규식 백트래킹·natural_key 타입 안전성·conftest parents 인덱스를 수동 추적으로 확인.
- Task 3: dispatched (haiku, BASE 1ab0989) — textfile.py 인코딩 폴백 + 본문 HTML 변환
- Task 3: minor (deferred): textfile.py:23-24 최종 폴백이 "utf-8" 이라 BOM+깨진바이트 동시 케이스에서 ﻿가 남을 수 있다. "utf-8-sig"로 바꾸면 해소. 필수 테스트 범위 밖, 비차단.
- Task 3: complete (commits 1ab0989..1249fd3, review clean — spec OK, quality Approved, Minor 1건 deferred)
- Task 4: dispatched (haiku, BASE 1249fd3) — video.py YouTube/Vimeo 링크 파싱
- Task 4: minor (deferred): video.py Vimeo id 추출이 leftmost 숫자 경로를 집어, 채널형 URL(vimeo.com/channels/32846/76979871)에서 채널 id를 video id로 잡는다. 브리프 범위 밖·레거시 형식, 비차단.
- Task 4: complete (commits 1249fd3..9ac18f4, review clean — spec OK, quality Approved, Minor 1건 deferred)
- Task 5: dispatched (haiku, BASE 9ac18f4) — dates.py git 업로드 시점 조회
- Task 5: review NG (2 Important) — (1) test_dates.py:26 약한 테스트: 함수가 항상 now()를 반환해도 통과한다. plan-mandated(브리프 Step 1 코드에서 유래). (2) dates.py:29 except가 UnicodeDecodeError를 놓쳐 text=True 디코딩 실패 시 예외가 전파된다 — "절대 예외를 던지지 않는다" 계약 위반.
- Task 5: Ruling: 두 Important 모두 수용하고 수정 루프에 넣는다. (1)은 내가 쓴 브리프의 결함이지만 스펙 11장이 요구하는 것은 "기대값을 실제로 판별하는 테스트"이고, 커밋 시각을 과거로 고정한 뒤 그 값에 근접함을 단정하면 폴백 구현을 잡아낼 수 있다 — 계획의 문장보다 스펙의 의도가 우선한다. (2)는 계약이 절대형("모든 실패 경로")으로 서술돼 확률적 예외를 허용하지 않으므로 errors=replace 또는 except 확대가 맞다. 틀렸을 경우의 비용: 테스트 강화가 과잉이었다면 테스트 한 개가 조금 더 길어질 뿐이고, 디코딩 가드가 불필요했다면 인자 하나가 남는다 — 양쪽 모두 되돌리기 쉽다.
- Task 5: fix round 1/5 (2 addressed, 0 open — 약한 테스트/UnicodeDecodeError; commits 83e310d..9b9a63b). 재리뷰어가 env 병합(os.environ.copy + update)까지 확인.
- Task 5: complete (commits 9ac18f4..9b9a63b, review clean)
- Task 6: dispatched (sonnet — 3개 모듈 통합 + 13 테스트, BASE 9b9a63b) — scanner.py 업로드 폴더 2단 스캔
- Task 6: review Important 1건 (plan-mandated) — scan()이 OS 수준 I/O 실패(깨진 symlink에서 iterdir, PermissionError, TOCTOU)에서 예외를 던질 수 있어 브리프의 굵은 글씨 계약 "어떤 입력에도 예외를 던지지 않는다"를 위반. 브리프 Step 3 참조 구현에 동일한 구멍이 있었다.
- Task 6: Ruling: 수용하고 수정 루프에 넣는다. 스펙이 계약을 절대형으로 서술했고, 이 저장소 경로가 Desktop/cloud/... 아래라 클라우드 동기화 폴더에서 로컬 빌드를 돌릴 가능성이 실재한다(placeholder 파일·TOCTOU). 가드는 try/except OSError 두 곳으로 끝나는 값싼 변경이고, Task 11의 build()도 scan() 예외를 잡지 않으므로 지금 막는 편이 맞다. 다만 이식성 있는 진짜 트리거가 없는 경로에 mock 전용 테스트를 넣는 것은 금지하고, 없으면 없다고 보고하게 한다. 틀렸을 경우의 비용: 불필요한 try/except 두 개가 남는다 — 되돌리기 쉽다.
- Task 6: minor (deferred): 모든 게시물이 스킵된 카테고리가 통째로 빠지는 경로(scanner.py:185-188)가 테스트되지 않음(커버리지 갭, 동작은 검사상 정상).
- Task 6: minor (deferred): 카테고리 비었음 경고가 접두사 붙은 원본 폴더명을 쓰고 다른 경고는 파싱된 제목을 써서 문체가 불일치. 업로드 경로가 파일일 때 '업로드 폴더가 없습니다' 문구를 재사용해 약간 오해 소지.
- Task 6: fix round 1/5 dispatched (원 구현자 재개)
- Task 6: fix round 1/5 (1 addressed, 0 open — I/O 가드; commits 661fe00..f9194d8). 재리뷰어가 경고가 scan() 반환값까지 도달하는 경로 3개를 모두 추적, 새 테스트가 skip이 아니라 PASSED임을 직접 실행해 확인.
- Task 6: complete (commits 9b9a63b..f9194d8, review clean, 45 tests)
- Task 7: dispatched (haiku, BASE f9194d8) — images.py 커버 16:9 크롭·갤러리 리사이즈·유튜브 썸네일
- Task 7: cannot-verify 항목(전체 스위트) 컨트롤러가 직접 실행해 해소: 55 passed, 경고 없음.
- Task 7: minor (deferred): 16:9 fit 계산이 make_cover와 fetch_youtube_cover에 동일하게 중복. _fit_cover 헬퍼로 묶으면 해소.
- Task 7: minor (deferred): 프로덕션 차이 — i.ytimg.com은 maxresdefault가 없을 때 404가 아니라 200 + 작은 플레이스홀더를 주는 것으로 알려져 있어, hqdefault 폴백이 안 타고 저품질 커버가 성공으로 보고될 수 있다. 네트워크 없는 테스트로는 재현 불가.
- Task 7: complete (commits f9194d8..232e59a, review clean — Minor 3건 deferred)
- Task 8: dispatched (sonnet — scanner+images 통합, 정렬 규칙, BASE 232e59a) — manifest.py
- Task 8: implementer가 DONE_WITH_CONCERNS로 보고 — 브리프의 테스트가 7개인데 계획/dispatch가 8개(전체 63)라고 적었다. 구현자가 숫자를 맞추려 가짜 8번째 테스트를 만들지 않고 보고한 것은 올바른 판단.
- Task 8: Ruling: 계획의 숫자가 틀렸다. 컨트롤러가 직접 확인(grep -c def test_ = 7, pytest = 62 passed)하고 계획 문서의 기대치를 7/62로 정정한다. manifest 커버리지는 스펙 11장 요구(정렬·스키마·증분·깨진 이미지·UTF-8)를 이미 모두 덮으므로 테스트를 추가하지 않는다. 틀렸을 경우의 비용: 없음 — 코드는 그대로고 문서 숫자만 바뀐다.
- Task 8: minor (deferred): manifest.py 유튜브 커버 분기가 h를 round(COVER_WIDTH*9/16)로 재계산한다(브리프 코드 그대로). 현재는 fetch_youtube_cover가 정확히 그 크기로 저장하므로 일치하지만, images.COVER_RATIO가 바뀌면 조용히 틀린 h가 나온다. image_size(cover_dest) 읽기로 바꾸면 다른 경로와 provenance가 통일된다.
- Task 8: minor (deferred): date=None 둘인 경우를 덮는 테스트 없음(추론상 안전 — 튜플 비교가 == 로 단축).
- Task 8: complete (commits 232e59a..c753430, review clean — Minor 2건 deferred, 62 tests)
- Task 9: implementer가 계획 내부 모순을 보고 — test_게시물_페이지는_상대경로로_자산을_참조한다 는 figure src에 한글 원문 경로를 기대하고, test_게시물_OG_태그는_절대주소를_쓴다 는 퍼센트 인코딩을 기대한다. _url_path를 일률 적용하면 전자가 실패한다. 구현자는 _url_path를 OG 절대 URL 두 곳으로만 좁히고 나머지는 html.escape만 적용하는 쪽을 선택해 보고했다.
- Task 9: Ruling: 인코딩 쪽이 이긴다. 모든 로컬 URL에 _url_path를 일률 적용하고, 한글 원문을 기대하던 테스트의 기대치를 인코딩 형태로 고친다(앞서 OG 테스트에 한 것과 동일한 정정). 근거: 폴더 이름은 작가가 임의로 짓는 입력이고 이름에 # ? & 나 공백이 들어가면 원문 href는 조용히 깨진다(# 이후가 프래그먼트로 잘림). html.escape는 그 문자들을 건드리지 않으므로 이스케이프만으로는 막을 수 없다. 규칙을 하나로 두는 편이 추론도 쉽다. 파일시스템 경로와 링크 텍스트는 한글 원문을 유지하고 URL만 인코딩한다. Task 11 linkcheck가 unquote 후 해석하므로 정합적이다. 틀렸을 경우의 비용: 생성된 HTML의 주소가 읽기 어려워지는 것뿐이고, 브라우저 주소창에는 여전히 한글로 보인다 — _url_path 호출부를 되돌리면 복구된다.
- Task 9: complete (commits 8a39d89..32b9d37, review clean — spec OK, quality Approved, 77 tests). 리뷰어가 이스케이프 5경로·인코딩 경계·상대깊이·OG 누락처리·prev/next 카테고리 스코프를 모두 코드로 추적.
- Task 9: minor (deferred): render.py:258 gridPageSize가 0일 때 or 연산자 때문에 '누락'과 같게 취급되어 기본값 8로 대체된다. is None 검사로 바꾸면 해소.
- Task 9: minor (deferred): len(works) == gridPageSize 경계, 빈 about/contactNote, works가 0인 카테고리를 덮는 테스트 없음(코드는 검사상 정상).
- Task 9: minor (deferred): test_이전_다음_링크가_연결된다 가 href 값과 첫 게시물의 prev 부재를 확인하지 않아 다른 테스트보다 약하다(브리프에서 유래).
- Task 9: cannot-verify 항목이 실제 결함으로 확인됨 — kind=='file' 영상이 사이트 산출물로 복사되지 않는다. scanner가 video.url에 파일명만 담고(scanner.py:107), 어떤 태스크도 mp4를 media/로 옮기지 않으며, upload/는 Jekyll 배포에서 제외돼 있다. 결과: 로컬 mp4 게시물의 src가 사이트 루트의 없는 파일을 가리키고, Task 11의 linkcheck가 이를 깨진 참조로 잡아 빌드가 종료코드 1로 실패한다.
- Task 6/8: Ruling: 스펙의 구멍이다(4장은 mp4 재생을 지원한다고 하고 3장은 upload/를 배포에서 제외한다 — 동시에 성립 불가). mp4 지원을 버리지 않고 manifest 단계에서 영상 파일을 media/로 복사하고 video.url을 사이트 루트 기준 상대경로로 바꾼다. mp4 지원은 사용자가 명시적으로 요구한 결정이라 조용히 축소할 수 없고, upload/의 어떤 것도 서빙하지 않는다는 규칙을 하나로 유지하는 편이 낫다. 비용은 저장소에 영상이 2배로 쌓이는 것(웹 업로드 상한 25MB이므로 최악 50MB)이고, 스펙 12장에 media/를 CDN으로 옮기는 탈출구가 이미 문서화돼 있다. 틀렸을 경우의 비용: 저장소 용량 — 되돌리려면 복사 단계를 지우고 대신 upload/ 배포 제외를 푸는 쪽으로 바꾸면 된다.
- Task 8 후속 수정 dispatched (원 Task 8 구현자 재개) — manifest.py에 영상 파일 복사
- Task 8 후속 수정: fix round 1/5 (1 addressed, 0 open — 영상 파일 media 복사; commits 32b9d37..c365c28, 78 tests). 재리뷰어가 in-place 변형 없음·copy2 mtime 보존으로 증분 게이트 동작·실패 시 video 필드를 통째로 드롭해 깨진 src가 생길 수 없음을 확인.
- 컨트롤러 정리: __pycache__/.pytest_cache 를 .gitignore에 추가(915375c). Task 12의 git add -A portfolio 가 이들을 커밋에 섞는 것을 사전 차단.
- Task 10: dispatched (haiku, BASE 915375c) — assets/css/style.css + assets/js/app.js (다크 고정 스타일, 더보기·라이트박스)
- Task 10: complete (commits 915375c..08412d4, review clean — spec OK, quality Approved). 리뷰어가 템플릿 4개+render.py를 직접 읽어 셀렉터를 양방향 대조: 불일치 0건. .js 게이트 방향을 render.py의 실제 'card extra' 출력과 맞춰 확인. 팔레트가 채널 델타 <=4로 실제 무채색임도 확인.
- Task 10: minor (deferred): 라이트박스에 포커스 트랩과 오픈 시 포커스 이동이 없어, 키보드 사용자가 Tab으로 오버레이 뒤 페이지 요소로 이동할 수 있다. 닫을 때 포커스 복귀는 정상이라 갇히지는 않음. 브리프 요구 범위 밖.
- Task 10: minor (deferred): 화살표 순환(wraparound)과 이미지 클릭 시 닫힘이 의도임을 표시하는 주석 없음.
- Task 11: dispatched (sonnet — 통합 태스크, BASE 08412d4) — linkcheck.py + build.py CLI + 전체 파이프라인 테스트
- Task 11: Ruling: build.py의 UTF-8 스트림 재설정(브리프 외 추가)을 그대로 수용한다. CP949 로케일에서 파이프된 자식 프로세스가 로케일 인코딩으로 출력해 UnicodeDecodeError가 실제로 발생했고, 테스트에서 자식의 인코딩으로 디코딩하는 대안은 테스트의 맹점만 메우고 CLI 자체는 호스트 기본 인코딩에 의존하게 남긴다. CI가 파싱하는 출력이므로 도구가 항상 UTF-8을 내보내는 편이 옳다. 가드(hasattr + AttributeError/ValueError/OSError 포착)가 io.UnsupportedOperation까지 덮어 진짜 no-op이고, 리눅스 러너에서는 멱등이다. 틀렸을 경우의 비용: 블록 한 개(9줄)를 지우면 복구된다.
- Task 11: cannot-verify 항목(--check 미빌드 경로) 컨트롤러가 직접 실행해 해소: '생성된 페이지가 없습니다. 먼저 빌드하세요.' + exit 1.
- Task 11: minor (deferred): linkcheck 정규식이 큰따옴표 속성만 매칭한다(현재 템플릿은 전부 큰따옴표라 미노출). 후행 슬래시 없는 디렉터리 참조는 Path.exists()가 True라 index.html 없이도 통과한다(현재 그런 참조를 만들지 않음). build.py의 스트림 재설정이 import 시점 모듈 수준에 있어 라이브러리로 import하면 프로세스 전역 stdout을 바꾼다(현재 import하는 곳 없음).
- Task 11: complete (commits 08412d4..34d90f0, review clean — 90 tests)
- Task 12: dispatched (sonnet, BASE 34d90f0) — Actions 워크플로 + 작가용 README + 최종 검증. Step 6(브라우저 육안 확인)과 Step 8(사용자 확인 사항)은 컨트롤러가 처리.
- Task 12: review NG (Important 2건, 둘 다 plan-mandated) — (1) README의 '만지지 않아도 되는 것' 목록이 about.html/contact.html을 빠뜨렸다. 이 둘도 render.py:311-312가 매번 생성하고 워크플로가 커밋하므로, 작가가 GitHub 웹에서 직접 편집하면 다음 업로드 때 아무 설명 없이 사라진다. 게다가 '이름·연락처 바꾸기' 절이 site.config.json의 about/contactNote 키를 지목하지 않아 올바른 경로도 안내되지 않는다. (2) 실패 확인 안내가 없다 — 반영이 안 될 때 Actions 탭을 보라는 한 줄이 없어 작가에게 진단 경로가 없다.
- Task 12: Ruling: 두 건 모두 수용하고 수정 루프에 넣는다. (1)은 비개발자에게 조용한 데이터 손실을 일으키는 함정이고, README가 존재하는 이유 자체가 그것을 막는 것이다. (2)는 스펙이 이 문서를 '사이트가 계속 갱신되는지를 결정하는 산출물'로 규정했으므로 실패 시 진단 경로가 없으면 그 목적을 달성하지 못한다. 둘 다 README 몇 줄 추가로 끝나고 코드 변경이 없다. 틀렸을 경우의 비용: 문서가 조금 길어지는 것뿐.
- Task 12: fix round 1/5 dispatched (원 구현자 재개)
- Task 12: fix round 1/5 (2 addressed, 0 open — README 생성파일 목록·실패 확인 안내; commits 20f0f2f..3e0b730). 재리뷰어가 render.py/textfile.py를 직접 읽어 빈 줄 단락 규칙 서술이 사실임을 확인하고, 생성 파일 6개 집합이 워크플로 git add 목록과 1:1 일치함을 확인.
- Task 12: complete (commits 34d90f0..3e0b730, review clean, 90 tests)
- 전체 12개 태스크 완료. 전체 브랜치 리뷰 준비.

## 전체 브랜치 리뷰 (opus) 결과와 판정
- 컨트롤러가 Critical #1을 직접 확인: requirements 파일 없음, 워크플로는 pillow만 설치한 뒤 pytest 실행 -> 첫 실행 무조건 실패. 이 워크플로는 main에만 트리거되고 이 브랜치는 푸시된 적이 없어 한 번도 실행되지 않았다.
- Ruling: 단일 수정 웨이브로 다음을 고친다 — #1 pytest 설치, #2 카테고리 슬러그 전역 중복 해소, #3 push 전 fetch+rebase, #4 없는 디렉터리 git add, #5 커버 없을 때 플레이스홀더(스펙 4/10장이 요구했으나 미구현), #7 유튜브 썸네일 존재 검사+image_size(및 _save를 try 안으로), #9 repo_root를 git rev-parse로 도출+스펙 12장 정정+README 링크, #10 라이트박스 재진입 가드+포커스 이동, #11 설정 파싱 실패 한국어 처리, T3 utf-8-sig, T4 Vimeo 마지막 숫자 세그먼트, video poster, 슬러그 위생(빈값/./..), README의 거짓 서술 2건, pillow/pytest 버전 고정+timeout.
- Ruling: #6(생성물 정리 미구현)은 구현하지 않고 README에 문서화한다 — 자동 삭제는 스캔 경고로 폴더가 스킵된 순간 그 작업물의 산출물을 지워버릴 수 있어, 조용한 데이터 손실을 고치려다 더 위험한 조용한 삭제를 만든다. 틀렸을 경우의 비용: 지운 작업물의 주소가 남아 있고, 내려달라는 요청에 폴더 삭제만으로는 대응이 안 된다 — README에 그 사실을 적어 사용자가 알고 대응하게 한다.
- Ruling: #8(CI에서 증분 게이트 무효)은 파킹한다 — 산출물은 바이트 동일하므로 정확성 문제가 아니라 비용 문제이고, 제대로 고치려면 소스 크기·해시를 manifest에 저장해 상태를 하나 더 만들어야 한다. 작업물 수십 개 규모에서는 Actions 시간이 감당 가능하다. 틀렸을 경우의 비용: 업로드마다 전체 재인코딩으로 Actions 분이 선형 증가 — 느려지면 manifest에 크기·mtime을 기록하는 쪽으로 바꾼다.
- Ruling: #12(file:// 탐색 불가)는 주소를 index.html로 바꾸지 않고 서술을 정정한다 — 예쁜 주소는 공유될 때마다 영구히 보이는 것이고 file:// 탐색은 일회성 편의다. 스펙/README에 '자산 참조는 상대경로라 폴더째 옮길 수 있으나 카드 탐색은 웹 서버가 필요하다(python -m http.server)'로 적는다. 틀렸을 경우의 비용: 로컬에서 클릭 탐색을 못 하는 것 — 한 줄 명령으로 우회된다.
- Ruling: Pretendard 웹폰트(스펙 9장)는 넣지 않고 스펙을 정정한다 — 외부 폰트는 '외부 참조 없음/오프라인 동작' Global Constraint와 충돌한다. 시스템 한글 폰트 스택을 유지한다. 틀렸을 경우의 비용: 한글 본문이 맑은 고딕으로 보인다.
- Ruling: ogImage(사이트 루트 링크 미리보기 이미지 없음)는 파킹 — 지인이 자기 이미지를 줘야 하는 콘텐츠다. 스펙 13장 미결정 목록에 남는다.
- 나머지 Minor(.mov 재생, link.txt 줄 시작 매칭, .js FOUC, _site의 README/config 노출, card.replace 문자열 수술, gridPageSize 0, generatedAt 커밋 노이즈, T1 커밋 trailer, T6/T7/T8/T9/T11 커버리지·중복 항목)는 파킹. 리뷰어의 triage와 일치.
- 리뷰어가 내 판정 6건 전부에 동의(T9 인코딩·T6/T8 mp4 포함). 다만 mp4 판정의 문서 후속(README의 '원본은 웹에 공개되지 않습니다'가 영상에는 거짓)이 누락됐다고 지적 — 수정 웨이브에 포함.
- 최종 수정 웨이브 dispatched (단일 에이전트, sonnet, BASE 3e0b730)
- 최종 수정 웨이브: 재리뷰 결과 A1~E7 14건 전부 ADDRESSED, 새 Critical/Important 없음 (commits 3e0b730..9ef99cb, 104 tests). 구현자 우려 2건도 수용 가능 판정: rebase 충돌은 bash -eo pipefail 때문에 push 전에 중단되어 안전하게 실패하고, 커밋 메시지 오타는 amend 금지 원칙이 우선.
- Ruling(파킹): test_커버가_없으면_경고를_남긴다 는 이 웨이브 이전에도 존재했던 동작을 검사한다 — 결함은 아니지만 B2/C4의 증거는 아니다. 남겨둔다. 틀렸을 경우의 비용: 없음(테스트 하나가 다른 것을 검사하고 있을 뿐).
- Ruling(파킹): style.css의 폰트 스택 첫 항목에 Pretendard 이름이 남아 있어, 스펙 9장의 'OS 기본 산세리프로만' 문장이 문자 그대로는 정확하지 않다(그 이름의 폰트를 시스템에 설치한 방문자에게만 적용). 웹폰트를 로드하지 않으므로 실질 무해. 틀렸을 경우의 비용: 스펙 문장과 CSS 한 줄의 미세한 불일치 — 이름을 지우거나 문장을 완화하면 해소.
- Ruling(파킹): A2 실패 시 복구 경로가 README에 없다(작가는 빨간 표시를 보고 알리기만 하면 되고, 워크플로 재실행이나 workflow_dispatch는 안내되지 않음). 14개 findings에 포함되지 않았고 두 번째 수정 웨이브는 없다. 틀렸을 경우의 비용: 업로드가 연달아 두 번 들어와 충돌하면 사용자가 Actions 탭에서 재실행해야 하고 작가는 그 이유를 모른다 — 사용자에게 최종 보고로 알린다.
- Ruling(파킹): D1은 site.config.json이 UTF-8이 아닐 때의 UnicodeDecodeError를 잡지 않는다(지정 범위 밖). GitHub 웹 편집은 UTF-8로 저장하므로 위험 낮고, 어느 경우든 빌드는 눈에 보이게 실패한다.
