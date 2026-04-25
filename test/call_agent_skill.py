from core.agent_skills.agent_skills_LLM import AgentSkillsLLM
from core.agent_skills.skills_manager import SkillsManager
from model.qwen_llm import llm
"""
https://github.com/NicholasSpisak/second-brain/tree/main/skills

https://github.com/lxyzsl/AI-AgentSkills-Study.git
"""
def main():
    # 技能系统初始化
    skill_manager = SkillsManager("./skills",debug=True)
    agent = AgentSkillsLLM(llm, skill_manager,debug=True)
    print("\n🚀 AgentSkills (LangChain 版) 已启动！")
    print(agent.chat("上海天气"))

if __name__ == "__main__":

    main()
