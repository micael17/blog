## VS Code 소스 코드가 오픈소스인 걸 알고 계셨나요?

> **원본 레포**: [microsoft/vscode](https://github.com/microsoft/vscode) · ⭐ 184,723 · TypeScript · MIT
> **Reddit r/programming**: [548 pts, 182 comments](https://reddit.com/r/programming/comments/1t49srb/update_on_coauthoredby_copilot_in_commit_messages/)

### TL;DR
- 전 세계 개발자 대부분이 매일 쓰는 VS Code의 핵심 코드가 GitHub에 완전 공개되어 있습니다.
- Microsoft가 배포하는 VS Code와 오픈소스 `Code - OSS`는 엄밀히 다른 빌드이지만, 소스는 동일합니다.
- 별 184,723개를 받은 이 레포는 단순 공개를 넘어, 로드맵·이슈·PR까지 실시간으로 공유되는 진짜 의미의 오픈 개발입니다.

---

### 이게 뭔가

`microsoft/vscode`는 Visual Studio Code의 소스 레포지토리입니다. 단순히 코드가 올라와 있는 저장소가 아니라, Microsoft 팀이 실제로 이 레포에서 개발을 진행하고, 월간 이터레이션 계획과 엔드게임 플랜까지 위키에 공개합니다. 즉, 제품 개발 프로세스 자체가 투명하게 열려 있습니다.

엄밀히 말하면 구분이 필요합니다. 이 레포는 `Code - OSS`라 불리는 MIT 라이선스 코어입니다. 우리가 실제로 내려받는 VS Code 설치파일은 여기에 Microsoft 전용 기능(원격 측정, 마켓플레이스 연동 등)을 얹어 별도 라이선스로 배포한 빌드입니다. 오픈소스 코어는 완전히 쓸 수 있지만, 그 위에 얹은 서비스 레이어는 다릅니다.

---

### 왜 지금 화제인가

Reddit r/programming에서 548 포인트를 받으며 다시 주목받고 있습니다. 2015년 9월 첫 공개 이후 10년 넘게 꾸준히 커밋이 이어지고 있고, 마지막 푸시가 오늘(2026-05-09)인 만큼 여전히 활발하게 관리되는 레포입니다. 별 184,723개는 GitHub 전체에서도 손꼽히는 수치입니다. AI 코딩 보조 기능이 에디터 생태계의 핵심 경쟁지로 떠오르면서, VS Code의 확장 모델과 내부 구조에 관심을 갖는 개발자가 늘고 있는 것도 한 이유입니다.

---

### 누가 써야 하나

- **VS Code 확장을 만들고 싶은 개발자**: 내장 확장들(`extensions/` 폴더)의 실제 구현을 참고하면 공식 문서보다 훨씬 구체적인 패턴을 배울 수 있습니다.
- **에디터 기능에 버그를 발견한 개발자**: 이슈를 올리거나 PR을 직접 올릴 수 있습니다. 오픈 이슈 17,384개 중 `good first issue` 라벨이 붙은 항목부터 시작하면 기여 진입장벽이 낮습니다.
- **자체 에디터 또는 IDE 도구를 만들려는 팀**: Language Server Protocol 구현, TextMate 문법 처리, 디버그 어댑터 프로토콜 등 에디터 인프라 코드를 실제 프로덕션 수준에서 볼 수 있습니다.

---

### 빠르게 써보기

소스에서 직접 빌드해 실행하는 방법입니다.

```bash
# 전제: Node.js 20+, Git, Python 3 설치 필요

git clone https://github.com/microsoft/vscode.git
cd vscode

# 의존성 설치 (처음 한 번만)
npm install

# 빌드 및 실행
./scripts/code.sh        # macOS/Linux
# 또는
.\scripts\code.bat       # Windows
```

Dev Container를 쓰면 환경 설정 없이 바로 시작할 수 있습니다.

```bash
# Docker가 설치된 경우, VS Code에서 레포를 열면
# "컨테이너에서 다시 열기" 프롬프트가 자동으로 뜹니다.
# 빌드에 필요한 권장 사양: 4코어 CPU, 8GB RAM
```

---

### 비슷한 도구와 비교

| | VS Code (Code-OSS) | Zed | Neovim |
|---|---|---|---|
| 기반 기술 | Electron + TypeScript | Rust (GPU 렌더링) | C (Lua 설정) |
| 확장 생태계 | 매우 풍부 | 초기 단계 | 풍부하지만 복잡 |
| 성능 | 무겁지만 기능 완성도 높음 | 가볍고 빠름 | 가벼움, 학습 곡선 있음 |
| AI 통합 | GitHub Copilot 기본 탑재 | 자체 AI 기능 실험 중 | 플러그인 의존 |

Zed는 성능 측면에서 VS Code를 압박하고 있지만, 확장 생태계 크기와 기업 지원 면에서는 아직 격차가 큽니다.

---

### 한 줄 평

매일 쓰는 도구의 내부가 이렇게 열려 있다는 사실만으로도 가볼 만하고, 확장 개발이나 에디터 인프라에 관심 있다면 읽어볼 코드가 무궁무진합니다. **적합**.

---

### 참고 및 출처

- **GitHub 레포**: [microsoft/vscode](https://github.com/microsoft/vscode)
- **Reddit r/programming**: https://reddit.com/r/programming/comments/1t49srb/update_on_coauthoredby_copilot_in_commit_messages/

본 글은 위 GitHub 레포의 README와 소셜 토론(HN/Reddit)을 바탕으로 한국 독자를 위해 한국어로 정리·분석한 글입니다. 가장 정확한 최신 정보는 원본 레포를 직접 확인해주세요.
