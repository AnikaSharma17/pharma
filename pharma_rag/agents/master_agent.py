from crewai import Agent, Crew, Process, Task, LLM
from pharma_rag.agents.worker_agents import PharmaAgents
from pharma_rag.utils.report_schema import FinalReport
from pharma_rag.tools.graph_rag_tool import GraphRAGTool
from typing import List, Dict, Any, Union

# Requirement 4: Task Monitoring & Logging using Callback functions
class MyCustomCallback:
    """
    A custom callback handler to monitor agent and task execution.
    """
    def on_task_start(self, task: Task, **kwargs):
        print(f"\n--- [TASK START] ---")
        print(f"Task: {task.description}\n")

    def on_task_end(self, task: Task, output: Any, **kwargs):
        print(f"\n--- [TASK END] ---")
        print(f"Agent: {task.agent.role}")
        print(f"Task Output: \n{output}\n---------------------\n")
    
    def on_agent_step(self, agent: Agent, tool: str, input: Dict[str, Any], output: Any, **kwargs):
        print(f"\n--- [AGENT STEP] ---")
        print(f"Agent: {agent.role}")
        print(f"Tool: {tool}")
        print(f"Tool Input: {input}")
        print(f"Tool Output: {output}\n")


class MasterAgent:
    def __init__(self, llm: LLM, tools: List[GraphRAGTool]):
        self.llm = llm
        # Pass tool instances to PharmaAgents so worker agents can use them
        self.pharma_agents = PharmaAgents(llm, tools=tools)
        self.master_agent = Agent(
            role='Innovation Strategy Orchestrator',
            goal='Orchestrate research tasks and synthesize complex findings from all worker agents into a single, structured report suitable for a C-level executive.',
            backstory="""You are the lead AI strategist responsible for repurposing innovation. You excel at taking fragmented data, connecting the dots, and crafting compelling business narratives.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )

    def run_strategy(self, query: str):

        logging_callback = MyCustomCallback()

        # 1. Define Task
        market_task = Task(
            description=f"Analyze market viability and patient unmet need score for the query: '{query}'. Focus on low competition areas.",
            agent=self.pharma_agents.iqvia_exim_agent(),
            expected_output="A structured JSON object detailing the top 3 molecules/diseases with high unmet need and low competition, including patient population data.",
        )

        ip_clinical_task = Task(
            description="For the top molecule identified, investigate its complete clinical trial status, current patent expiry dates, and regulatory status. Check for any internal toxicity flags.",
            agent=self.pharma_agents.clinical_patent_agent(), 
            context=[market_task], # <--- THIS IS WHERE THE MARKET CONTEXT IS FED
            expected_output="A list of key patent IDs, their expiry dates, and a summary of the molecule's highest achieved clinical phase.",
        )
        
        research_task = Task(
            description=f"Initial comprehensive investigation for the query: '{query}'. Use all tools to gather data on target molecules, trials, patents, and market competition.",
            agent=self.pharma_agents.clinical_patent_agent(), # Example delegation
            expected_output="A structured list of promising molecules, their clinical phase, and key competitor patents found.",
        )

        synthesis_task = Task(
            description=f"Synthesize the Market Data, IP status, and Clinical status into a single, highly structured JSON object ready for report generation.",
            agent=self.master_agent,
            context=[market_task, ip_clinical_task],
            # Enforcement of Pydantic Schema
            output_json=FinalReport,
            expected_output="A final JSON string conforming to the FinalReport Pydantic schema, containing at least one opportunity."
        )

        # 2. Assemble Crew and Run
        project_crew = Crew(
            agents=[self.master_agent, self.pharma_agents.clinical_patent_agent(), self.pharma_agents.iqvia_exim_agent()], # Add all worker agents here
            tasks=[research_task, synthesis_task],
            process=Process.sequential,
            verbose=True,  # Changed from verbose=2 for CrewAI compatibility
            callbacks=[logging_callback]
        )

        result = project_crew.kickoff()
        return result