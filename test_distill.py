import json

# Test distilled text for output/ schema
with open(r'output/Adarsh_Jha_Resume (3).json', encoding='utf-8') as f:
    d = json.load(f)

lines = []
lines.append("Name: " + str(d.get("name", "")))
lines.append("Branch: " + str(d.get("branch", "")) + " | College: " + str(d.get("current_college_name", "")) + " | CGPA: " + str(d.get("current_college_cgpa", "")))
lines.append("Primary domain: " + str(d.get("primary_domain", "")) + " | Top domains: " + str(d.get("top_3_domains", "")))

skill_cats = [
    'webdev','frontend','backend','mobile_dev','app_dev','cloud','devops','data_science',
    'machine_learning','deep_learning','reinforcement_learning','computer_vision','nlp',
    'cybersecurity_cryptography','blockchain_web3','bioinformatics','ar_vr',
    'robotics_automation','big_data','digital_electronics','analog_circuits','vlsi_design',
    'embedded_systems','signal_processing','control_systems','iot','communication_systems',
    'power_systems_power_electronics','quantum_computing','digital_twins_simulation_tools'
]
scores = []
for cat in skill_cats:
    v = d.get(cat + "_score", 0) or 0
    if v > 0:
        scores.append(cat.replace("_", " ") + ":" + str(v))
lines.append("Skill scores: " + ", ".join(scores))

lines.append("Languages: " + str(d.get("net_known_languages", "")))
lines.append("Tools: " + str(d.get("net_tools_technologies", "")))
lines.append("Courses: " + str(d.get("relevant_coursework", "")))
lines.append("Certs: " + str(d.get("certifications_list", "")))

for i in range(1, 6):
    t = d.get("project_" + str(i) + "_title")
    desc = d.get("project_" + str(i) + "_description") or ""
    tools = d.get("project_" + str(i) + "_tools") or ""
    if t:
        short_desc = desc[:200]
        lines.append("Project: " + t + ". " + short_desc + " [" + tools + "]")

for i in range(1, 5):
    c = d.get("work_" + str(i) + "_company")
    role = d.get("work_" + str(i) + "_role") or ""
    desc = d.get("work_" + str(i) + "_description") or ""
    tools = d.get("work_" + str(i) + "_tools") or ""
    if c:
        short_desc = desc[:200]
        lines.append("Work: " + role + " at " + c + ". " + short_desc + " [" + tools + "]")

lines.append("Awards: " + str(d.get("awards_list", "")))
lines.append("POR: " + str(d.get("por_positions_list", "")))

text = "\n".join(l for l in lines if l and str(None) not in l)
print("--- DISTILLED TEXT (output/ schema) ---")
print(text)
print("\n--- STATS ---")
print("Characters:", len(text))
print("Estimated tokens:", len(text)//4)

# Also test worst case: the biggest manual_text file
print("\n\n--- manual_text worst case: SHAKTI SHREY ---")
with open(r'manual_text/SHAKTI SHREY.json', encoding='utf-8') as f:
    m = json.load(f)

m_lines = []
m_lines.append("Name: " + str(m.get("student_name", "")))
m_lines.append("Skills: " + str(m.get("skills", ""))[:500])
m_lines.append("Courses: " + str(m.get("courses", ""))[:300])
m_lines.append("Other info: " + str(m.get("other_info", ""))[:400])

# Projects raw text truncated
proj_raw = ""
proj_data = m.get("projects", {})
if isinstance(proj_data, dict):
    proj_raw = proj_data.get("raw_text", "") or ""
elif isinstance(proj_data, str):
    proj_raw = proj_data

# Get first 600 chars of project raw text
m_lines.append("Projects: " + proj_raw[:600])

m_text = "\n".join(l for l in m_lines if l and str(None) not in l)
print(m_text)
print("\nCharacters:", len(m_text))
print("Estimated tokens:", len(m_text)//4)
