"""
ADK regulatory agent adapter.

This module attempts to detect a native ADK/GenAI ADK API and prefer it when
available. If a native ADK agent API is not present, the module provides a
CrewAI-based fallback `ADKRegulatoryAgent` implementation so the project
remains runnable and Agent-to-Agent (A2A) calls still work.

Usage:
    from pharma_rag.agents.adk_regulatory_agent import ADKRegulatoryAgent

Notes:
- If you intend to use a vendor ADK (e.g., Google ADK/genai.adk), install the
  correct package and ensure it exposes an `Agent`-like API. This adapter will
  try common construction patterns automatically.
"""

import importlib
from typing import List, Any
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI


# Try several possible ADK import paths / symbols
_adk_module = None
ADK_AVAILABLE = False
for mod_name in ("google.genai.adk", "google.genai", "adk", "google_adk", "genai.adk"):
    try:
        _mod = importlib.import_module(mod_name)
        _adk_module = _mod
        # If module contains nested adk object, prefer that
        if hasattr(_mod, "adk"):
            _adk_module = getattr(_mod, "adk")
        break
    except Exception:
        _mod = None

# Heuristic: check for Agent-like factory/signature
if _adk_module is not None:
    ADK_AVAILABLE = any(hasattr(_adk_module, name) for name in ("Agent", "create_agent", "AgentClient", "create_adk_agent"))
else:
    ADK_AVAILABLE = False


# Requirement 3: Structured Output using Pydantic
class RegulatoryReport(BaseModel):
    """Pydantic model for the ADK agent's structured output."""
    molecule: str = Field(description="The molecule investigated.")
    status: str = Field(description="Approval status (e.g., Approved, Phase 3, Rejected).")
    key_indications: List[str] = Field(description="List of key indications.")
    summary: str = Field(description="A brief summary of the findings.")


class ADKRegulatoryAgent:
    """
    ADK compatibility wrapper.

    If a native ADK agent is detected, this adapter will attempt to instantiate
    and delegate to it. Otherwise it uses a CrewAI internal `Agent` to perform
    the regulatory reasoning so the code stays runnable.
    """

    def __init__(self, llm: ChatGoogleGenerativeAI, tools: List[Any]):
        self.llm = llm
        self.tools = tools
        self.adk_agent = None

        if ADK_AVAILABLE and _adk_module is not None:
            try:
                # Try common constructor patterns on the detected ADK module
                if hasattr(_adk_module, "Agent"):
                    try:
                        self.adk_agent = _adk_module.Agent(llm=self.llm, tools=self.tools)
                    except Exception:
                        try:
                            self.adk_agent = _adk_module.Agent()
                        except Exception as e:
                            print(f"Warning: ADK Agent exists but could not be constructed: {e}")
                elif hasattr(_adk_module, "create_agent"):
                    try:
                        self.adk_agent = _adk_module.create_agent(llm=self.llm, tools=self.tools)
                    except Exception:
                        try:
                            self.adk_agent = _adk_module.create_agent()
                        except Exception as e:
                            print(f"Warning: ADK create_agent failed: {e}")
            except Exception as e:
                print(f"Warning: ADK module detected but initialization failed: {e}")

        # CrewAI fallback
        if self.adk_agent is None:
            self.internal_worker = Agent(
                role='Regulatory Affairs Specialist',
                goal='Determine the current regulatory approval status, key indications, and relevant regulatory submission history for a molecule.',
                backstory=(
                    "You are an expert on FDA, EMA, and regional regulatory guidelines. "
                    "You are an expert at multi-hop reasoning on complex knowledge graphs."
                ),
                llm=self.llm,
                tools=self.tools,
                verbose=True,
            )

    def run_regulatory_check(self, query: str, molecule: str) -> str:
        """Main entrypoint for A2A calls. Delegates to native ADK agent if available."""
        print(f"\n---  [A2A Call] ADK Agent Received Task: Check {molecule} ---\n")

        # Try to delegate to native ADK agent if present
        unstructured_result = None
        if getattr(self, "adk_agent", None) is not None:
            adk_agent = self.adk_agent
            for method in ("run", "execute", "__call__", "handle", "ask"):
                if hasattr(adk_agent, method):
                    try:
                        fn = getattr(adk_agent, method)
                        try:
                            result = fn(query=query, molecule=molecule)
                        except TypeError:
                            result = fn(f"{query} | molecule: {molecule}")
                        unstructured_result = result
                        print(f"Delegated regulatory check to ADK agent via {method}().")
                        break
                    except Exception as e:
                        print(f"Warning: ADK agent method {method} failed: {e}")

        # CrewAI fallback if ADK could not be used or didn't return a result
        if unstructured_result is None:
            task = Task(
                description=(
                    f"For the molecule '{molecule}' (related to the overall query: '{query}'), "
                    "determine its current regulatory approval status, key indications, and regulatory history."
                ),
                agent=self.internal_worker,
                expected_output="A summary of approval status, key indications, and history.",
            )

            internal_crew = Crew(
                agents=[self.internal_worker],
                tasks=[task],
                process=Process.sequential,
                verbose=0,
            )

            unstructured_result = internal_crew.kickoff()

        # Format into Pydantic schema using another CrewAI agent to enforce structure
        formatter_agent = Agent(
            role="JSON Formatter",
            goal=f"Format the following text into the RegulatoryReport JSON schema: {unstructured_result}",
            backstory="You are a JSON formatting expert.",
            llm=self.llm,
            output_json=RegulatoryReport,
            verbose=False,
        )

        format_task = Task(
            description=f"Format this text: {unstructured_result}",
            agent=formatter_agent,
            expected_output="A JSON object matching the RegulatoryReport schema.",
        )

        format_crew = Crew(agents=[formatter_agent], tasks=[format_task], process=Process.sequential)
        json_result = format_crew.kickoff()

        print(f"\n---  [A2A Response] ADK Agent Returning: {json_result} ---\n")
        return json_result