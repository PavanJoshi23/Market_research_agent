# I2M Research Agent — Architecture & Flow

> Tavily API POC · Research Agent (Agent 01) of the Idea-to-Market Engine

---

## 1. High-Level Graph Topology

```mermaid
flowchart TD
    START([START]) --> intake

    intake["intake
    validate and normalise idea"]

    intake --> router["research_router
    Send fan-out"]

    router -->|Send| MS["market_sizing
    TAM · SAM · SOM"]
    router -->|Send| CM["competitor_matrix
    3 to 5 competitors"]
    router -->|Send| RA["risk_analysis
    regulatory and adoption risks"]

    MS --> merge["merge_research
    LLM synthesis"]
    CM --> merge
    RA --> merge

    merge --> END([END])
    merge --> outputs["outputs folder
    idea_timestamp.md"]
```

---

## 2. Parallel Execution Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant G as LangGraph
    participant MS as market_sizing
    participant CM as competitor_matrix
    participant RA as risk_analysis
    participant MR as merge_research

    U->>G: python main.py
    U->>G: Enter business idea
    G->>G: intake node validates idea

    G->>MS: Send parallel
    G->>CM: Send parallel
    G->>RA: Send parallel

    MS->>MS: Tavily search x2
    MS->>MS: AzureChatOpenAI extract
    MS-->>G: research_results append market_sizing

    CM->>CM: Tavily search x2
    CM->>CM: AzureChatOpenAI extract
    CM-->>G: research_results append competitor_matrix

    RA->>RA: Tavily search x2
    RA->>RA: AzureChatOpenAI extract
    RA-->>G: research_results append risk_analysis

    G->>MR: all 3 complete
    MR->>MR: AzureChatOpenAI synthesise
    MR-->>G: research_output final dict
    G-->>U: rich terminal tables
    G-->>U: outputs/idea_timestamp.md saved
```

---

## 3. State Flow Through the Graph

```mermaid
flowchart LR
    A["idea: str
    business idea text"]

    B["research_results: list
    operator.add reducer
    safe parallel append"]

    C["research_output: dict
    final ResearchOutput"]

    intake -->|sets| A
    market_sizing -->|appends| B
    competitor_matrix -->|appends| B
    risk_analysis -->|appends| B
    merge_research -->|reads B, sets| C
```

---

## 4. market_sizing Node Detail

```mermaid
flowchart TD
    MS_IN["idea: str"] --> T1

    T1["TavilySearch
    depth: advanced
    max_results: 7
    topic: general"]

    T1 --> Q1["Query 1
    idea + market size TAM SAM SOM"]
    T1 --> Q2["Query 2
    idea + industry revenue forecast"]

    Q1 --> CTX["Combined search context
    titles, URLs, snippets"]
    Q2 --> CTX

    CTX --> LLM1["AzureChatOpenAI
    MARKET_SIZING_PROMPT"]

    LLM1 --> OUT1["tam
    sam
    som
    growth_rate
    market_summary
    sources"]
```

---

## 5. competitor_matrix Node Detail

```mermaid
flowchart TD
    CM_IN["idea: str"] --> T2

    T2["TavilySearch
    depth: advanced
    max_results: 8
    topic: general"]

    T2 --> Q3["Query 1
    idea + top competitors alternatives"]
    T2 --> Q4["Query 2
    idea + competing startups pricing"]

    Q3 --> CTX2["Combined search context"]
    Q4 --> CTX2

    CTX2 --> LLM2["AzureChatOpenAI
    COMPETITOR_MATRIX_PROMPT"]

    LLM2 --> OUT2["competitors list
    name, description
    pricing
    strengths
    weaknesses
    sources"]
```

---

## 6. risk_analysis Node Detail

```mermaid
flowchart TD
    RA_IN["idea: str"] --> T3

    T3["TavilySearch
    depth: basic
    max_results: 6
    topic: news
    time_range: year"]

    T3 --> Q5["Query 1
    idea + regulatory risks legal 2024 2025"]
    T3 --> Q6["Query 2
    idea + market adoption barriers"]

    Q5 --> CTX3["Combined search context
    recent news articles"]
    Q6 --> CTX3

    CTX3 --> LLM3["AzureChatOpenAI
    RISK_ANALYSIS_PROMPT"]

    LLM3 --> OUT3["risks list
    risk description
    category
    severity high mid low
    mitigation
    sources"]
```

---

## 7. merge_research and Output

```mermaid
flowchart TD
    R1["market_sizing result
    tam, sam, som, growth_rate"] --> MERGE
    R2["competitor_matrix result
    competitors list"] --> MERGE
    R3["risk_analysis result
    risks list"] --> MERGE

    MERGE["merge_research
    AzureChatOpenAI
    MERGE_PROMPT
    deduplicate sources
    write executive_summary"]

    MERGE --> FINAL["ResearchOutput
    executive_summary
    tam, sam, som
    competitors list
    risks list
    sources list"]

    FINAL --> TERM["Rich terminal
    tables and panels"]

    FINAL --> MD["outputs folder
    idea_timestamp.md
    Executive Summary
    Market Sizing table
    Competitor Matrix table
    Risk Analysis table
    Sources"]
```

---

## 8. Project File Structure

```mermaid
flowchart TD
    ROOT["tavily api/"]

    ROOT --> MAIN["main.py
    CLI entry point
    prompts for idea
    streams graph events
    saves markdown report"]

    ROOT --> ENV[".env.example
    TAVILY_API_KEY
    AZURE_OPENAI vars"]

    ROOT --> REQ["requirements.txt"]

    ROOT --> SRC["src/"]

    SRC --> STATE["state.py
    ResearchState TypedDict
    operator.add on research_results"]

    SRC --> TOOLS["tools.py
    market_tool advanced
    competitor_tool advanced
    risk_tool basic plus news"]

    SRC --> PROMPTS["prompts.py
    MARKET_SIZING_PROMPT
    COMPETITOR_MATRIX_PROMPT
    RISK_ANALYSIS_PROMPT
    MERGE_PROMPT"]

    SRC --> NODES["nodes.py
    intake
    market_sizing
    competitor_matrix
    risk_analysis
    merge_research"]

    SRC --> GRAPH["graph.py
    StateGraph
    research_router with Send
    compiled research_graph"]

    ROOT --> OUT["outputs/
    per-run markdown files"]

    ROOT --> BRAIN[".brain/
    architecture.md"]
```
