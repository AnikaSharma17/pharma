from crewai import Agent
from crewai.tools import tool
from pharma_rag.tools.graph_rag_tool import GraphRAGTool
from typing import Any, List, Callable
from crewai.tools import tool as crew_tool
from pharma_rag.agents.adk_regulatory_agent import ADKRegulatoryAgent

@tool
def pdf_formatter(json_data: str):
    """Converts the final JSON into a PDF-like formatted string."""
    return f"Formatted Report Content:\n{json_data}"

# This function creates and wraps the ADK agent in a CrewAI-compatible Tool.
def setup_adk_tool(llm, tools: list[Any]) -> Any:
    
    # 1. Instantiate the ADK agent
    adk_agent_instance = ADKRegulatoryAgent(llm=llm, tools=tools)
    
    # 2. Create a CrewAI Tool that calls the ADK agent's method
    @tool("ADKRegulatoryCheck")
    def adk_regulatory_check_tool(query: str, molecule: str) -> str:
        """
        Calls the external ADK Regulatory Agent to get approval status, indications,
        and history for a specific molecule. This tool bridges CrewAI and ADK frameworks.
        Input must be the original query and the specific molecule to check.
        """
        # This is the A2A (Agent-to-Agent) call
        return adk_agent_instance.run_regulatory_check(query=query, molecule=molecule)
    
    return adk_regulatory_check_tool

class PharmaAgents:
    """
    Defines all the specialized Worker Agents for the pharmaceutical innovation acceleration system.
    """

    def __init__(self, llm, tools: List[Any] | None = None):
        self.llm = llm
        self.tools = tools or []

        # Resolve graph RAG tool instance if provided and expose callable wrappers
        self.research_tools: List[Callable] = []
        graph_tool_instance = None
        for t in self.tools:
            if isinstance(t, GraphRAGTool):
                graph_tool_instance = t
                break

        if graph_tool_instance:
            # Wrap instance methods as simple callables expected by agents
            self.research_tools.append(lambda q, gt=graph_tool_instance: gt._run_semantic_search(q))
            self.research_tools.append(lambda q, gt=graph_tool_instance: gt._run_graph_query(q))
        else:
            # Placeholders - agents can still call these but they'll raise if used
            def _missing(*args, **kwargs):
                raise RuntimeError("GraphRAGTool not configured")
            self.research_tools = [_missing, _missing]

        # ADK tool placeholder (may be set up externally); provide a safe CrewAI tool
        def _adk_missing(query: str, molecule: str) -> str:
            raise RuntimeError("ADK regulatory tool not configured")

        # Wrap as a CrewAI tool instance so Agent validation accepts it
        self.adk_tool = crew_tool("MissingADK")(_adk_missing)

        # Expose the GraphRAGTool instance itself as a CrewAI tool (preferred)
        if graph_tool_instance:
            self.graph_tool = graph_tool_instance
        else:
            # Create a missing-graph CrewAI tool to satisfy Agent schema
            def _missing_graph(query: str, tool_type: str = "semantic") -> str:
                raise RuntimeError("GraphRAGTool not configured")
            self.graph_tool = crew_tool("MissingGraph")(_missing_graph)

    def clinical_patent_agent(self):
        """Investigates clinical trial status, patent landscape, and IP expiration dates."""
        return Agent(
            role='Clinical Trial and Patent Analyst',
            goal='Investigate the complete clinical trial status, patent landscape, and IP expiration dates for any given molecule or disease area.',
            backstory="""You are a meticulous analyst specializing in multi-jurisdictional intellectual property and clinical development data. You are an expert at multi-hop reasoning on complex knowledge graphs.""",
            llm=self.llm,
            # pass the actual GraphRAG tool instance (or a missing placeholder)
            tools=[self.graph_tool, self.adk_tool],
            verbose=True,
            allow_delegation=True
        )


    def iqvia_exim_agent(self):
        """Analyzes market competition, patient population, and sales trends."""
        return Agent(
            role='Market Insights and Commercial Analyst',
            goal='Analyze market competition scores, patient population, sales trends, and commercial potential for molecules in specific markets.',
            backstory="""You possess deep knowledge of IQVIA and EXIM data structures, excelling at quantitative analysis and identifying unmet market needs and low-competition areas.""",
            llm=self.llm,
            # Use the GraphRAGTool instance (it will accept args for structured/semantic)
            tools=[self.graph_tool],
            verbose=True,
            allow_delegation=True
        )
    
    def internal_knowledge_agent(self):
        """Retrieves and analyzes proprietary internal company data."""
        return Agent(
            role='Internal Knowledge Retrieval Specialist',
            goal='Retrieve proprietary internal data, such as toxicity screens, synthesis reports, or internal trial failure analyses, relevant to the current investigation.',
            backstory="""You are the guardian of internal R&D history, capable of finding crucial context within proprietary documents to inform go/no-go decisions.""",
            llm=self.llm,
            # Use the GraphRAGTool instance (it will accept args for structured/semantic)
            tools=[self.graph_tool],
            verbose=True,
            allow_delegation=False # Should not delegate proprietary tasks
        )
    
    
    def report_generation_agent(self):
        """
        Creates the final, structured PDF report from synthesized data.
        Note: This agent will use a specific tool (not defined here, but conceptually
        ReportLab/WeasyPrint) to format the PDF based on the final JSON output.
        """
        return Agent(
            role='Executive Report Generation Specialist',
            goal='Take the final, synthesized JSON object from the Master Agent and format it into a professional, structured PDF or printable summary.',
            backstory="""You are a master of communication, ensuring complex findings are presented clearly, concisely, and with a business-focused narrative suitable for C-level executives.""",
            llm=self.llm,
            # We assume a specific PDF/ReportLab tool here, but for crewai we use a generic Tool
            tools=[pdf_formatter],
            verbose=True,
            allow_delegation=False
        )

# EOF (This file contains the worker agents definitions)