## Claude Code의 두뇌를 DeepSeek으로 바꾸기 — 같은 UX, 비용 17분의 1

> **원본 레포**: [aattaran/deepclaude](https://github.com/aattaran/deepclaude) · ⭐ 1,018 · JavaScript · MIT
> **Hacker News**: [650 pts, 273 comments](https://news.ycombinator.com/item?id=48002136)

### TL;DR
- Claude Code의 자율 에이전트 기능을 그대로 쓰면서, AI 추론을 DeepSeek V4 Pro로 대체해 비용을 최대 90% 줄인다.
- 환경 변수 몇 줄만 바꾸는 방식이라 Claude Code의 파일 편집·bash 실행·서브에이전트 루프는 전혀 건드리지 않는다.
- DeepSeek 외에 OpenRouter, Fireworks AI, 원본 Anthropic까지 세션 중단 없이 실시간 전환된다.

---

### 이게 뭔가

Claude Code는 현재 시장에서 가장 완성도 높은 자율 코딩 에이전트로 꼽힌다. 파일 읽기·편집, 터미널 실행, 서브에이전트 분기, git 연동까지 하나의 루프 안에서 돌아간다. 문제는 가격이다. Anthropic Max 플랜은 월 200달러인데 사용량 상한까지 있고, API로 직접 쓰면 출력 토큰 기준 100만 개당 15달러다.

deepclaude는 여기서 딱 한 곳만 건드린다. Claude Code가 API 호출 대상을 결정하는 환경 변수(`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, 모델명 변수들)를 세션 시작 시 DeepSeek 엔드포인트로 바꿔치기한 뒤, 세션이 끝나면 원래 값으로 복원한다. Claude Code 본체는 수정이 없다. 두뇌만 교체하고 몸통은 그대로 두는 구조다.

DeepSeek V4 Pro는 LiveCodeBench 기준 96.4%를 기록하며, 출력 토큰 가격은 100만 개당 0.87달러다. Anthropic 대비 약 17배 저렴하다. 게다가 DeepSeek은 동일 컨텍스트가 반복될 때 자동 캐싱이 적용되어, 에이전트 루프에서 시스템 프롬프트와 파일 컨텍스트가 누적될수록 실효 비용이 더 내려간다(캐싱 적용 시 100만 토큰당 0.004달러).

---

### 왜 지금 화제인가

레포가 생성된 건 2026년 5월 3일, 마지막 푸시는 하루 뒤인 5월 4일이다. 이틀도 안 돼 GitHub 별 1,018개를 찍었고, Hacker News에서는 650포인트·273개 댓글로 당일 상위권에 올랐다. DeepSeek V4 Pro가 공개된 직후 Claude Code 사용자들이 비용 문제를 토로하던 시점과 맞물렸고, "Claude Code의 UX를 포기하지 않아도 된다"는 메시지가 HN 커뮤니티에서 강하게 공명한 것으로 보인다.

---

### 누가 써야 하나

- **Claude Code 헤비유저**: 월 200달러 플랜 한도를 자주 초과하거나, API 사용량이 많아 청구서가 부담스러운 개발자.
- **사이드 프로젝트 개발자**: 본업 외에 개인 프로젝트를 에이전트로 돌리고 싶은데, 비용이 발목을 잡던 상황. 월 5달러 크레딧으로 시작해볼 수 있다.
- **팀 도입 검토 중인 기술 리드**: 조직 전체에 Claude Code를 도입하기 전 비용 구조를 실험해보고 싶은 경우. 무거운 reasoning이 필요한 태스크만 `--backend anthropic`으로 돌리고 나머지는 DeepSeek으로 처리하는 혼합 전략이 가능하다.

---

### 빠르게 써보기

**1. DeepSeek API 키 발급**

[platform.deepseek.com](https://platform.deepseek.com)에서 가입 후 5달러 크레딧 충전, API 키 복사.

**2. 환경 변수 설정**

```bash
# macOS/Linux
echo 'export DEEPSEEK_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

```powershell
# Windows PowerShell
setx DEEPSEEK_API_KEY "sk-your-key-here"
```

**3. 설치**

```bash
# macOS/Linux
git clone https://github.com/aattaran/deepclaude
cd deepclaude
chmod +x deepclaude.sh
sudo ln -s "$(pwd)/deepclaude.sh" /usr/local/bin/deepclaude
```

**4. 실행**

```bash
deepclaude                   # DeepSeek V4 Pro로 Claude Code 시작
deepclaude --status          # 백엔드 현황 및 API 키 확인
deepclaude --cost            # 가격 비교표 출력
deepclaude --backend or      # OpenRouter 사용 (미국 서버, 최저가)
deepclaude --backend anthropic  # 원본 Claude Opus 복귀
```

세션 중 백엔드 전환이 필요하면 `~/.claude/commands/`에 슬래시 커맨드 파일을 추가하면 Claude Code 터미널 안에서 `/deepseek`, `/anthropic`을 직접 입력해 전환할 수 있다.

**비용 추적 확인:**

```bash
curl -s http://127.0.0.1:3200/_proxy/cost
```

응답 예시:
```json
{
  "total_cost": 0.0941,
  "anthropic_equivalent": 1.05,
  "savings": 0.9559
}
```

---

### 비슷한 도구와 비교

| 도구 | 접근 방식 | 차별점 |
|---|---|---|
| **LiteLLM** | 프록시 서버로 모델 라우팅 | 범용적이지만 Claude Code 특화 설정이 없음 |
| **Aider** | Claude Code 대신 쓸 수 있는 별도 에이전트 | 직접 대체품. Claude Code의 tool loop와 UX는 포기해야 함 |
| **deepclaude** | Claude Code 환경 변수 intercept | Claude Code 본체를 유지하면서 모델만 교체 |

핵심 차별점은 "Claude Code를 버리지 않는다"는 것이다. Aider나 Cline 같은 대안은 Claude Code와 에이전트 품질 차이가 있고, LiteLLM은 Claude Code에 맞게 직접 설정해야 하는 부분이 많다. deepclaude는 이 설정을 스크립트 한 줄로 처리한다.

---

### 한 줄 평

**적합**: Claude Code를 이미 쓰고 있고 비용이 실제 부담인 개발자에게는 지금 당장 설치할 이유가 충분하다. 단, 이미지 입력·MCP 서버 툴·Anthropic의 `cache_control` 프롬프트 캐싱은 지원되지 않으며, 복잡한 추론 태스크에서 DeepSeek이 Opus보다 뒤처지는 경우가 있다는 점은 감안해야 한다. "80%는 DeepSeek, 20%는 Anthropic"이라는 전략으로 쓰면 비용과 품질을 모두 잡을 수 있다.

---

### 참고 및 출처

- **GitHub 레포**: [aattaran/deepclaude](https://github.com/aattaran/deepclaude)
- **Hacker News 토론**: https://news.ycombinator.com/item?id=48002136

본 글은 위 GitHub 레포의 README와 소셜 토론(HN/Reddit)을 바탕으로 한국 독자를 위해 한국어로 정리·분석한 글입니다. 가장 정확한 최신 정보는 원본 레포를 직접 확인해주세요.
