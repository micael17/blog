`★ Insight ─────────────────────────────────────`

> **원본 레포**: [antirez/ds4](https://github.com/antirez/ds4) · ⭐ 3,360 · C · MIT
> **Hacker News**: [483 pts, 152 comments](https://news.ycombinator.com/item?id=48050751)
> **Reddit r/LocalLLaMA**: [112 pts, 46 comments](https://reddit.com/r/LocalLLaMA/comments/1t72tk9/ds4_a_deepseek_4_flash_specific_inference_engine/)

antirez는 Redis 창시자 Salvatore Sanfilippo의 GitHub 계정입니다. 그가 직접 LLM 추론 엔진을 C로 작성했다는 것 자체가 이 프로젝트의 핵심 화제성입니다. README에 "GPT 5.5의 강력한 보조를 받아 개발했다"고 명시한 점도 이례적입니다.
`─────────────────────────────────────────────────`

---

## Redis 창시자가 3일 만에 만든 로컬 AI 추론 엔진, ds4.c

### TL;DR
- Redis를 만든 antirez가 DeepSeek V4 Flash를 Mac에서 직접 돌리기 위해 C로 만든 초경량 추론 엔진.
- 범용 프레임워크 없이 이 모델 하나만 겨냥해 설계했고, 128GB MacBook Pro에서 실제로 동작한다.
- KV 캐시를 RAM이 아닌 SSD에 저장하는 방식으로 100만 토큰 컨텍스트를 로컬에서 현실적으로 다룬다.

---

### 이게 뭔가

`ds4.c`는 DeepSeek V4 Flash 모델 하나만을 위해 만들어진 Metal 기반 로컬 추론 엔진이다. llama.cpp처럼 GGUF를 범용으로 읽는 구조가 아니고, 특정 모델에 최적화된 Metal 그래프 실행기, 전용 KV 상태 관리, HTTP 서버 API까지 한 파일(`ds4.c`)에 녹여냈다.

작성자가 이 모델을 굳이 단독 엔진으로 만든 이유를 README에 직접 밝히고 있다. DeepSeek V4 Flash는 284B 파라미터의 MoE 구조지만 활성화되는 파라미터가 적어 빠르고, 사고(thinking) 구간이 문제 복잡도에 비례해 늘어나며(다른 모델 대비 최대 1/5 수준), KV 캐시 압축률이 높아 로컬 머신에서 긴 컨텍스트를 다루는 데 유리하다. 2비트 양자화를 해도 코딩 에이전트 수준에서 실용적으로 동작한다는 점도 직접 검증한 내용을 담고 있다.

---

### 왜 지금 화제인가

2026년 5월 6일에 저장소가 생성됐고, 이 글을 쓰는 시점(5월 9일)까지 3일 만에 별 3,360개를 받았다. Hacker News에서 483 포인트, 댓글 152개로 프론트페이지를 장악했고, r/LocalLLaMA에도 112 포인트를 기록했다. 화제의 중심은 기술 자체만큼이나 "Redis 창시자가 왜 LLM 추론 엔진을?"이라는 의외성이다. antirez는 README에 "GPT 5.5의 강력한 보조를 받아 개발했다"고 공개적으로 밝혔는데, 유명 오픈소스 개발자가 AI 보조 개발을 이렇게 투명하게 명시한 것도 커뮤니티의 화제가 됐다.

---

### 누가 써야 하나

- **Mac Studio / MacBook Pro 128GB 이상 보유자**: q2 양자화(약 81GB) 기준으로 128GB 머신에서 실행 가능하고, M3 Ultra 512GB 머신에서는 q4도 동작한다. Apple Silicon 없이는 쓸 수 없다.
- **로컬 코딩 에이전트를 구축하려는 개발자**: Claude Code, opencode, Pi 등의 에이전트를 OpenAI/Anthropic 호환 API로 ds4-server에 연결해서 클라우드 API 비용 없이 코딩 어시스턴트를 운용할 수 있다.
- **긴 컨텍스트 워크플로가 필요한 연구자**: 100만 토큰 컨텍스트 창을 디스크 KV 캐시와 조합하면, 서버 재시작 후에도 이전 프리필 결과를 재사용해 비용을 줄일 수 있다. 대규모 코드베이스 분석이나 문서 처리에 유용하다.

---

### 빠르게 써보기

**1. 저장소 클론 및 모델 다운로드**

```sh
git clone https://github.com/antirez/ds4
cd ds4

# 128GB 머신 → q2, 256GB 이상 → q4
./download_model.sh q2
```

**2. 빌드**

```sh
make
```

**3. CLI로 바로 실행**

```sh
# 단발성 프롬프트
./ds4 -p "Redis Streams를 한 문단으로 설명해줘."

# 대화형 멀티턴 세션
./ds4
ds4> /think      # 사고 모드 켜기
ds4> /nothink   # 사고 모드 끄기
ds4> /quit
```

**4. 로컬 서버 띄우기 (OpenAI/Anthropic 호환)**

```sh
./ds4-server \
  --ctx 100000 \
  --kv-disk-dir /tmp/ds4-kv \
  --kv-disk-space-mb 8192
```

```sh
# curl로 확인
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "안녕하세요"}],
    "stream": true
  }'
```

**5. Claude Code에 연결하기**

아래 내용을 `~/bin/claude-ds4`로 저장하고 실행 권한을 준다.

```sh
#!/bin/sh
unset ANTHROPIC_API_KEY

export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"
export ANTHROPIC_AUTH_TOKEN="dsv4-local"
export ANTHROPIC_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

exec "$HOME/.local/bin/claude" "$@"
```

```sh
chmod +x ~/bin/claude-ds4
~/bin/claude-ds4
```

`★ Insight ─────────────────────────────────────`
디스크 KV 캐시 키는 토큰 ID의 SHA1 해시입니다. 텍스트가 아닌 토큰 단위로 키를 만들기 때문에, 동일한 프롬프트가 다시 들어오면 프리필을 건너뛰고 저장된 상태를 그대로 씁니다. Claude Code가 매 요청마다 보내는 ~25k 토큰 시스템 프롬프트가 첫 요청 이후 사실상 무료가 되는 이유입니다.
`─────────────────────────────────────────────────`

**실측 속도 (MacBook Pro M3 Max 128GB, q2 기준)**

| 시나리오 | 프리필 | 생성 |
|---|---|---:|
| 짧은 프롬프트 | 58.52 t/s | 26.68 t/s |
| 11,709 토큰 프롬프트 | 250.11 t/s | 21.47 t/s |

---

### 비슷한 도구와 비교

**llama.cpp**와 비교하면, llama.cpp는 수백 가지 모델을 지원하는 범용 런타임인 반면 ds4.c는 DeepSeek V4 Flash 하나만 지원한다. 대신 이 모델에 한해서 공식 구현과 로짓 수준으로 검증된 정확도와 디스크 KV 캐시 같은 특화 기능을 제공한다. ds4.c가 직접 링크하지는 않지만, GGUF 포맷과 양자화 커널은 llama.cpp의 유산을 명시적으로 차용했다고 README에 밝혀 놓았다.

**Ollama**와 비교하면 편의성은 Ollama가 압도적으로 앞선다. ds4.c는 macOS Metal 환경에서 직접 빌드해야 하고, 사용 가능한 GGUF 파일도 프로젝트 전용 배포본만 쓸 수 있다. 반면 Ollama는 아직 DeepSeek V4 Flash 전체 규모를 로컬에서 실용적으로 돌리기 어렵다. 128GB 머신에서 284B급 모델을 실제로 실행할 수 있다는 점 자체가 ds4.c의 핵심 가치다.

---

### 한 줄 평

Mac Studio나 128GB MacBook을 보유한 개발자라면 당장 써볼 만하다. 범용성은 없지만, 그게 장점이다. 클라우드 API 비용 없이 준프론티어급 모델을 로컬 에이전트 백엔드로 굴릴 수 있다는 시나리오는 이 프로젝트 전까지는 현실적이지 않았다.

---

### 참고 및 출처

- **GitHub 레포**: [antirez/ds4](https://github.com/antirez/ds4)
- **Hacker News 토론**: https://news.ycombinator.com/item?id=48050751
- **Reddit r/LocalLLaMA**: https://reddit.com/r/LocalLLaMA/comments/1t72tk9/ds4_a_deepseek_4_flash_specific_inference_engine/

본 글은 위 GitHub 레포의 README와 소셜 토론(HN/Reddit)을 바탕으로 한국 독자를 위해 한국어로 정리·분석한 글입니다. 가장 정확한 최신 정보는 원본 레포를 직접 확인해주세요.
