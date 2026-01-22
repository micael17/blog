/**
 * 게임/주변기기 트렌드 키워드 수집 스크립트
 * 실행: bun run scripts/collect.ts
 */

import googleTrends from "google-trends-api";
import { mkdir, writeFile } from "fs/promises";
import { existsSync } from "fs";

// 수집할 카테고리별 시드 키워드
const SEED_KEYWORDS = {
  마우스: ["게이밍 마우스", "로지텍 마우스", "무선 마우스"],
  키보드: ["기계식 키보드", "게이밍 키보드", "무접점 키보드"],
  헤드셋: ["게이밍 헤드셋", "무선 헤드셋"],
  모니터: ["게이밍 모니터", "144hz 모니터"],
  게임: ["스팀 게임", "PC 게임 추천"],
};

// 오늘 날짜 (YYYY-MM-DD)
const today = new Date().toISOString().split("T")[0];

interface TrendResult {
  keyword: string;
  category: string;
  relatedQueries: string[];
  risingQueries: string[];
}

async function getRelatedQueries(keyword: string): Promise<{ related: string[]; rising: string[] }> {
  try {
    const result = await googleTrends.relatedQueries({
      keyword,
      geo: "KR",
      hl: "ko",
    });

    const data = JSON.parse(result);
    const defaultData = data.default;

    const related = defaultData.rankedList?.[0]?.rankedKeyword?.map((item: any) => item.query) || [];
    const rising = defaultData.rankedList?.[1]?.rankedKeyword?.map((item: any) => item.query) || [];

    return { related: related.slice(0, 10), rising: rising.slice(0, 10) };
  } catch (error) {
    console.error(`  ⚠️ "${keyword}" 조회 실패:`, (error as Error).message);
    return { related: [], rising: [] };
  }
}

async function collectTrends(): Promise<TrendResult[]> {
  const results: TrendResult[] = [];

  for (const [category, keywords] of Object.entries(SEED_KEYWORDS)) {
    console.log(`\n📁 [${category}] 수집 중...`);

    for (const keyword of keywords) {
      console.log(`  🔍 "${keyword}" 조회...`);
      const { related, rising } = await getRelatedQueries(keyword);

      results.push({
        keyword,
        category,
        relatedQueries: related,
        risingQueries: rising,
      });

      // API 제한 방지 (1.5초 대기)
      await new Promise((r) => setTimeout(r, 1500));
    }
  }

  return results;
}

function generateMarkdown(results: TrendResult[]): string {
  let md = `# 트렌드 키워드 수집 결과\n\n`;
  md += `📅 수집일: ${today}\n\n`;
  md += `---\n\n`;

  // 카테고리별 그룹화
  const byCategory = results.reduce((acc, r) => {
    if (!acc[r.category]) acc[r.category] = [];
    acc[r.category].push(r);
    return acc;
  }, {} as Record<string, TrendResult[]>);

  for (const [category, items] of Object.entries(byCategory)) {
    md += `## ${category}\n\n`;

    for (const item of items) {
      md += `### ${item.keyword}\n\n`;

      if (item.risingQueries.length > 0) {
        md += `**🔥 급상승 키워드**\n`;
        item.risingQueries.forEach((q) => (md += `- ${q}\n`));
        md += `\n`;
      }

      if (item.relatedQueries.length > 0) {
        md += `**🔗 연관 키워드**\n`;
        item.relatedQueries.forEach((q) => (md += `- ${q}\n`));
        md += `\n`;
      }

      if (item.risingQueries.length === 0 && item.relatedQueries.length === 0) {
        md += `_데이터 없음_\n\n`;
      }
    }
  }

  return md;
}

async function main() {
  console.log("🚀 트렌드 키워드 수집 시작\n");

  // keywords 폴더 확인
  const keywordsDir = "./keywords";
  if (!existsSync(keywordsDir)) {
    await mkdir(keywordsDir, { recursive: true });
  }

  // 수집 실행
  const results = await collectTrends();

  // 마크다운 생성 및 저장
  const markdown = generateMarkdown(results);
  const filePath = `${keywordsDir}/${today}.md`;

  await writeFile(filePath, markdown, "utf-8");

  console.log(`\n✅ 수집 완료!`);
  console.log(`📄 저장 위치: ${filePath}`);
  console.log(`📊 수집된 키워드 그룹: ${results.length}개`);
}

main().catch(console.error);
