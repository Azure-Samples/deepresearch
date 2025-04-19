---
page_type: sample
languages:
- python
- javascript
- html
- css
products:
- azure-ai-inference
- langchain-azure-ai
- langgraph
- deepseek
urlFragment: deep-research
name: Azure Deep Research - Reasoning Research Assistant
description: An AI-powered, reasoning research assistant that conducts comprehensive web research, analyzes and synthesizes information with images using DeepSeek R1, langchain-azure-ai and LangGraph. 
---

# Azure Deep Research: Reasoning Research Assistant

This sample creates a reasoning, AI-powered reseacrher using [DeepSeek R1](https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/concepts/models#deepseek). Give it a topic and it will generate a web search query, gather web search results, summarise the results of web search, reflect on the summary to examine knowledge gaps, generate a new search query to address the gaps, search, and improve the summary for a user-defined number of cycles. It will provide the user a final markdown summary with all sources used. The sample uses [langchain-azure-ai](https://github.com/langchain-ai/langchain-azure), which allows us to access the [Azure AI Inference API](https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/overview) to use DeepSeek R1. [LangGraph](https://langchain-ai.github.io/langgraph/), Langchain's framework for building AI agents, is used to implement the reflection architecture. 

## Table of Contents

- [Features](#features)
- [Azure Account Requirements](#azure-account-requirements)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Environment Setup](#environment-setup)
- [Architecture](#architecture)
- [Usage](#usage)
- [Technical Implementation](#technical-implementation)
- [Security and Compliance](#security-and-compliance)
- [Resources](#resources)
- [Contributing](#contributing)
- [Code of Conduct](#code-of-conduct)
- [License](#license)

![research-process](./images/researcher-process.png)
![research-process](./images/research-report-image.png)


## Features

The Azure Deep Research project provides the following features:

* **Automated Multi-stage Research Process**: Conducts comprehensive research through a structured workflow including query generation, web search, summarization, and analysis
* **Real-time Research Progress Tracking**: Visual step-by-step tracking of the research process
* **AI Thinking Process Transparency**: Access to the AI's thought process via a dedicated thinking bubble interface
* **Comprehensive Report Generation**: Creates well-structured research reports with illustrative images
* **Responsive Design**: Fully responsive interface that works across devices

![Research Process Workflow](./images/deep_researcher_architecture.png)

## Azure Account Requirements

**IMPORTANT:** In order to deploy and run this project, you'll need:

* **Azure account**. If you're new to Azure, [get an Azure account for free](https://azure.microsoft.com/free/cognitive-search/) and you'll get some free Azure credits to get started.
* **Azure subscription with access enabled for the Azure OpenAI Service**. You'll need an Azure subscription with permission to access the [DeepSeek-R1](https://azure.microsoft.com/en-us/products/ai-services/openai-service/) model.
* **Tavily API key** for web research capabilities. You can get an API Key [here](https://app.tavily.com/home), with 1000 free credits

## Getting Started

### Prerequisites

* [Python 3.10+](https://www.python.org/downloads/)
* [FastAPI](https://fastapi.tiangolo.com/)
* [Node.js and npm](https://nodejs.org/) (for frontend dependencies)
* [Git](https://git-scm.com/downloads)

### Local Development

1. Clone the repository:

```bash
git clone https://github.com/yourusername/deep-research.git
cd deep-research
```

2. Create and activate a virtual environment:

```bash
python -m venv deep_research
source deep_research/bin/activate  # On Windows: deep_research\Scripts\activate
```

3. Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Environment Setup

1. Create a `.env` file in the project root and add your API keys:

```
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_API_KEY=your_azure_openai_key
TAVILY_API_KEY=your_tavily_api_key
```

2. Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

3. Open your browser and navigate to:

```
http://localhost:8000
```

## Architecture

Azure Deep Research uses a modern, cloud-based architecture:

- **Backend**: FastAPI server with WebSocket support for real-time communication
- **Frontend**: HTML, CSS, and JavaScript with responsive design
- **AI Models**: Azure OpenAI DeepSeek-R1 and GPT-4o for advanced reasoning
- **Research**: Tavily API for comprehensive web search
- **State Management**: LangGraph for structured research workflow

## Usage

1. Enter your research topic in the input field
2. Click "Research" to start the automated research process
3. Watch as the system progresses through multiple research stages
4. Review the detailed research report with embedded images
5. Access the AI's thinking process by clicking the thought bubble button

## Technical Implementation

Azure Deep Research uses a multi-step pipeline to deliver comprehensive research:

1. **Query Generation**: The system generates optimal search queries for the topic
2. **Web Research**: Multiple searches are conducted to gather information
3. **Summarization**: The AI analyzes and summarizes findings
4. **Reflection**: The system identifies knowledge gaps for further research
5. **Iteration**: Multiple research cycles are conducted for thoroughness
6. **Report Generation**: A final comprehensive report with images is created

The implementation leverages LangGraph for orchestrating the research workflow and WebSockets for real-time communication between the client and server.

## Security and Compliance

This project follows Azure security best practices:

- Input validation to prevent injection attacks
- Safe handling of API keys through environment variables
- No storage of personal data or research queries

## Resources

* [FastAPI Documentation](https://fastapi.tiangolo.com/)
* [Azure OpenAI Service Documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
* [LangGraph Documentation](https://python.langchain.com/docs/langgraph/)
* [Tavily API Documentation](https://docs.tavily.com/)

## Contributing

This project welcomes contributions and suggestions. Please fork the repository and submit a pull request for any improvements.

## Code of Conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).

For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
