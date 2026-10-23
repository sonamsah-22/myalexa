# MyAlexa Architecture

```mermaid
flowchart TD
    subgraph Clients["Clients"]
        AlexaPlus["Real Alexa+ (MCP Client)"]
        Simulator["Alexa+ Web Simulator UI (Voice / Text)"]
    </div>

    subgraph AgentRuntime["Agent & Orchestration Layer"]
        FastAPIProxy["FastAPI Proxy /chat Endpoint"]
        BedrockRuntime["Amazon Bedrock AgentCore Runtime"]
        StrandsAgent["Strands Agent Framework"]
        BedrockModel["Amazon Bedrock (Nova / Claude)"]
    </div>

    subgraph MCPLayer["MCP Server Layer (Stateless HTTP)"]
        MCPServer["Streamable HTTP MCP Server (port 8000 /mcp)"]
        StorageFactory["Storage Factory Abstraction"]
    </div>

    subgraph StorageLayer["Data Store"]
        MemoryDB["In-Memory Storage (Default / Local)"]
        DynamoDB["Amazon DynamoDB (Single Table 'planner')"]
    </div>

    %% Flows
    AlexaPlus -->|Streamable HTTP| MCPServer
    Simulator -->|POST /chat| FastAPIProxy
    FastAPIProxy --> StrandsAgent
    BedrockRuntime -->|AgentCore App| StrandsAgent
    StrandsAgent <-->|Invoke Model| BedrockModel
    StrandsAgent -->|MCP Client / MCP Tools| MCPServer
    MCPServer --> StorageFactory
    StorageFactory -->|STORAGE=memory| MemoryDB
    StorageFactory -->|STORAGE=dynamodb| DynamoDB
```
