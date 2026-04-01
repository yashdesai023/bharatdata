import { DatasetDefinition } from '../registry/types';
import { registry } from '../registry/registry-service';
import { CATEGORIES } from '@bharatdata/shared';

export interface UIQueryPlan {
  dataset: string | null;
  level: 'state' | 'district' | 'city' | 'national';
  filters: {
    state?: string | string[];
    district?: string | string[];
    city?: string | string[];
    year?: number;
    years?: number[] | string;
    category?: string | string[];
    [key: string]: any;
  };
  sort?: { 
    field: string; 
    order: 'asc' | 'desc'
  };
  limit?: number;
  queryComplexity?: 'simple' | 'comparison' | 'trend' | 'ranking' | 'exploration';
  comparison: boolean;
  trend: boolean;
  entities: string[];
  years: string[];
  chart_type: 'bar' | 'line' | 'map' | 'none';
  explanation: string;
}

/**
 * Translates a natural language question into a structured query plan.
 */
export async function generateQueryPlan(
  prompt: string,
  apiKey: string
): Promise<UIQueryPlan> {
  const datasets = registry.getSummaries();
  
  const systemPrompt = `You are the BharatData Query Planner for Indian government data. You translate natural language questions into structured API query plans. You never generate SQL. You only use provided datasets and fields.

Available datasets:
${JSON.stringify(datasets, null, 2)}

Available Categories (Strict Matches):
${CATEGORIES.join(', ')}

Available years: [2021, 2022, 2023]

Rules:
1. "level" must be 'state', 'district', 'city', or 'national' based on the question's granularity.
2. "filters" object keys must correspond to database columns like 'state', 'district', 'city', 'year', 'category'.
3. Use "years" (array of integers) for trend analysis across multiple years.
4. "UP" mean "Uttar Pradesh", "MH" means "Maharashtra", "DL" means "Delhi", etc.
5. "last year" means 2023.
6. CRITICAL: Your response must START with '{' and END with '}'. DO NOT use <think> tags. DO NOT explain your reasoning. DO NOT repeat your reasoning in loops.
7. VAGUE CATEGORY RULE: If the user says "crime" without specifying a category (like women, cyber, etc.), ALWAYS default to category "Total IPC Crimes".
8. VAGUE YEAR RULE: If no year is specified for a ranking, comparison, or record-fetch query, ALWAYS default to year 2023 (the latest year).
9. NO REASONING: Your response must contain ONLY the JSON object. DO NOT include <think> tags, DO NOT include explanations, and DO NOT repeat your logic in loops.
10. MULTIPLE CATEGORIES RULE: If the prompt asks to compare multiple categories (e.g., "cyber crime and crime against women"), pass an array of strings to the 'category' filter.

Return a JSON object only.

EXAMPLES:
1. "Crime in Maharashtra" -> { "dataset": "ncrb-crime-state", "level": "state", "filters": { "state": "Maharashtra", "year": 2023 }, "queryComplexity": "simple" }
2. "Comparison of cyber crime" -> { "dataset": "ncrb-crime-state", "level": "state", "filters": { "year": 2023, "category": "Cyber Crimes" }, "comparison": true, "queryComplexity": "comparison" }
3. "Murder trends in Delhi 2021-2023" -> { "dataset": "ncrb-crime-state", "level": "state", "filters": { "state": "Delhi", "years": [2021, 2022, 2023], "category": "Murder" }, "trend": true, "queryComplexity": "trend", "chart_type": "line" }
4. "Crime across top 5 states" -> { "dataset": "ncrb-crime-state", "level": "state", "filters": { "year": 2023, "category": "Total IPC Crimes" }, "sort": { "field": "total_cases", "order": "desc" }, "limit": 5, "queryComplexity": "ranking" }
5. "Compare cyber crime and crimes against women in UP" -> { "dataset": "ncrb-crime-state", "level": "state", "filters": { "state": "Uttar Pradesh", "year": 2023, "category": ["Cyber Crimes", "Crime Against Women"] }, "comparison": true, "queryComplexity": "comparison" }
6. "Total crime" -> { "dataset": "ncrb-crime-state", "level": "state", "filters": { "year": 2023, "category": "Total IPC Crimes" }, "queryComplexity": "exploration" }`;

  const response = await fetch('https://api.sarvam.ai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-subscription-key': apiKey
    },
    body: JSON.stringify({
      model: 'sarvam-m',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt }
      ],
      temperature: 0,
      max_tokens: 1024,
    })
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Sarvam API error: ${response.status} ${errorBody}`);
  }

  const result = await response.json() as any;
  let content = result.choices[0].message.content;

  // ROBUST JSON EXTRACTION: Find the balance of brackets { }
  // This will strip all reasoning noise, markdown, and tags even if malformed/unclosed.
  try {
    // 1. Strip reasoning tags if present
    content = content.replace(/<think>[\s\S]*?<\/think>/g, '');
    
    // 2. Find the first '{' and last '}' to extract the core JSON object
    const startIndex = content.indexOf('{');
    const endIndex = content.lastIndexOf('}');
    
    if (startIndex !== -1 && endIndex !== -1 && endIndex > startIndex) {
      const jsonStr = content.substring(startIndex, endIndex + 1);
      return JSON.parse(jsonStr) as UIQueryPlan;
    }
    
    // 3. Fallback if the model didn't return brackets
    return JSON.parse(content.trim()) as UIQueryPlan;
  } catch (e) {
    console.error('Failed to parse AI response as JSON:', content);
    throw new Error('AI returned an invalid response format. Please try rephrasing.');
  }
}

/**
 * Generates a narrative response from data.
 */
export async function generateNarrativeStream(
  userQuestion: string,
  queryPlan: UIQueryPlan,
  data: any[],
  apiKey: string
): Promise<ReadableStream> {
  const complexity = queryPlan.queryComplexity || 'simple';
  
  let analysisInstructions = '';
  if (complexity === 'trend') {
    analysisInstructions = `
- **Trend Analysis**: Calculate percentage changes between years. Identify if the trend is increasing, decreasing, or stable.
- **Outliers**: Note any years with significant deviations from the norm.`;
  } else if (complexity === 'comparison' || complexity === 'ranking') {
    analysisInstructions = `
- **Comparative Insights**: Rank the entities based on the values. Identify the top/bottom performers.
- **Gaps**: Highlight the scale of difference between the highest and lowest values (e.g., "X is 3x higher than Y").`;
  } else {
    analysisInstructions = `
- **Specific Insights**: Focus on the direct answer to the user's question. Call out the primary metric (total cases or rate).`;
  }

  const systemPrompt = `You are the BharatData Senior Analyst. Your task is to generate a comprehensive, professional, and well-formatted analysis.
  
  CRITICAL RULES:
  - DO NOT output <think> tags or any internal reasoning in the final output.
  - Deliver results in a clean, Sans-Serif friendly format.
  - Use Markdown TABLES (| State | Value |) for comparisons between multiple entities.
  - Use **Bold** for emphasis on critical numbers.
  - Use superscript citation markers (e.g. 1, 2, 3) for figures.
  
  User's Question: "${userQuestion}"
  Complexity: ${complexity}
  
  ANALYSIS INSTRUCTIONS:${analysisInstructions}
  - Provide a summary first.
  - Support every claim with numbers from the data.
  - Note any data limitations (nulls, missing years).
  
  Conclude with: "This analysis was generated from verified government statistics. Always verify critical data against primary sources."`;

  // Compress data payload to dramatically reduce API Token latency (up to 80% faster)
  const compressedData = data.map(d => ({
    l: d.district || d.state || d.city || 'Region',
    y: d.year,
    c: d.total_cases,
    r: d.rate_per_lakh
  })).slice(0, 100);

  const response = await fetch('https://api.sarvam.ai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-subscription-key': apiKey
    },
    body: JSON.stringify({
      model: 'sarvam-m',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: JSON.stringify(compressedData) }
      ],
      temperature: 0.1,
      max_tokens: 4000,
      stream: true
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('Narrative API Error:', response.status, errorText);
    throw new Error(`AI Narrative Generation Failed (Status: ${response.status})`);
  }

  return response.body!;
}
