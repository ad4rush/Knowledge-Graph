import os
import json
import glob

def generate_html():
    base_path = os.getcwd()
    output_dir = os.path.join(base_path, "output")
    manual_dir = os.path.join(base_path, "manual_text")
    
    students = []
    
    # Read all JSON files in output
    for file_path in glob.glob(os.path.join(output_dir, "*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                filename = os.path.basename(file_path)
                name = filename.replace(".json", "")
                
                # Clean up tools and companies
                raw_tools = data.get("net_tools_technologies", "")
                tools = []
                if raw_tools:
                    tools = list(set([t.strip() for t in raw_tools.split(";") if t.strip()]))
                    
                companies = []
                for i in range(1, 5):
                    comp = data.get(f"work_{i}_company")
                    if comp and isinstance(comp, str) and comp.strip():
                        companies.append(comp.strip())
                companies = list(set(companies))
                        
                domain = data.get("primary_domain")
                if not domain or not isinstance(domain, str):
                    domain = "general"
                elif domain == "vlsi_design":
                    hw_keys = ["digital_electronics_score", "analog_circuits_score", "signal_processing_score"]
                    best_hw = "vlsi_design"
                    best_score = data.get("vlsi_design_score") or 0
                    if not isinstance(best_score, (int, float)): best_score = 0
                    for k in hw_keys:
                        score = data.get(k, 0)
                        if score is not None and isinstance(score, (int, float)) and score > best_score:
                            best_hw = k.replace("_score", "")
                            best_score = score
                    domain = best_hw
                    
                students.append({
                    "id": name.replace(" ", "_").replace(".", ""),
                    "name": data.get("name") or name,
                    "domain": domain.lower().replace(" ", "_"),
                    "tools": tools,
                    "companies": companies,
                    "scores": {k: v for k, v in data.items() if k.endswith("_score") and isinstance(v, (int, float)) and v > 0},
                    "full_data": data
                })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    # Read JSON files in manual_text (different schema)
    for file_path in glob.glob(os.path.join(manual_dir, "*.json")):
        filename = os.path.basename(file_path)
        name = filename.replace(".json", "")
        # Skip if already processed from output
        if any(s["name"] == name or s["id"] == name.replace(" ", "_").replace(".", "") for s in students):
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                raw_tools = data.get("skills", "")
                tools = []
                if raw_tools and isinstance(raw_tools, str):
                    lines = raw_tools.split("\n")
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line and "endorsement" not in clean_line.lower() and "experience" not in clean_line.lower() and "associated with" not in clean_line.lower():
                            tools.append(clean_line)
                tools = list(set(tools))
                            
                students.append({
                    "id": name.replace(" ", "_").replace(".", "") + "_manual",
                    "name": data.get("student_name") or name,
                    "domain": "general", 
                    "tools": tools,
                    "companies": [],
                    "scores": {},
                    "full_data": data
                })
            except Exception as e:
                print(f"Error reading manual JSON {file_path}: {e}")
                
    students_json = json.dumps(students)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Knowledge Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
    <style>
        :root {{
            --bg-color: #0b0c10;
            --panel-bg: rgba(31, 40, 51, 0.85);
            --text-main: #c5c6c7;
            --accent: #66fcf1;
            --accent-dark: #45a29e;
            --dim-color: rgba(40, 45, 50, 0.5); /* Color for dimmed nodes */
        }}
        
        body, html {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow: hidden;
        }}

        #particles-js {{
            position: absolute;
            width: 100%;
            height: 100%;
            z-index: 1;
        }}

        #mynetwork {{
            position: absolute;
            width: 100%;
            height: 100%;
            z-index: 2;
        }}

        /* Search UI */
        #search-container {{
            position: absolute;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 20;
            width: 400px;
        }}

        #search-input {{
            width: 100%;
            padding: 15px 20px;
            font-size: 1.1rem;
            border-radius: 30px;
            border: 1px solid rgba(102, 252, 241, 0.3);
            background: rgba(11, 12, 16, 0.8);
            color: white;
            backdrop-filter: blur(10px);
            outline: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            box-sizing: border-box;
            transition: border-color 0.3s;
        }}
        
        #search-input:focus {{
            border-color: var(--accent);
        }}

        #search-suggestions {{
            position: absolute;
            top: 55px;
            left: 0;
            width: 100%;
            background: rgba(31, 40, 51, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            max-height: 300px;
            overflow-y: auto;
            display: none;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
        }}

        .suggestion-item {{
            padding: 12px 20px;
            cursor: pointer;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .suggestion-item:last-child {{ border-bottom: none; }}
        .suggestion-item:hover {{ background: rgba(102, 252, 241, 0.1); }}
        .suggestion-type {{ font-size: 0.8rem; color: var(--accent-dark); text-transform: uppercase; }}

        /* Top Left Controls */
        #controls {{
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 10;
        }}

        .btn {{
            padding: 10px 20px;
            background: rgba(31, 40, 51, 0.8);
            color: var(--accent);
            border: 1px solid rgba(102, 252, 241, 0.3);
            border-radius: 8px;
            cursor: pointer;
            backdrop-filter: blur(5px);
            transition: all 0.2s;
            font-weight: bold;
        }}
        .btn:hover {{
            background: rgba(102, 252, 241, 0.2);
            border-color: var(--accent);
            color: white;
        }}

        /* Glassmorphism Panel */
        #side-panel {{
            position: absolute;
            top: 20px;
            right: -400px; /* hidden by default */
            width: 350px;
            height: calc(100% - 40px);
            background: var(--panel-bg);
            backdrop-filter: blur(10px);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px 0 0 15px;
            box-shadow: -5px 0 15px rgba(0,0,0,0.5);
            z-index: 10;
            transition: right 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }}

        #side-panel.open {{
            right: 0;
        }}

        .panel-header {{
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .panel-header h2 {{
            margin: 0;
            color: var(--accent);
            font-size: 1.5rem;
        }}

        .close-btn {{
            background: none;
            border: none;
            color: var(--text-main);
            font-size: 1.5rem;
            cursor: pointer;
            transition: color 0.2s;
        }}
        .close-btn:hover {{ color: white; }}

        .panel-content {{
            padding: 20px;
            flex-grow: 1;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 5px;
            margin-bottom: 5px;
            background: rgba(102, 252, 241, 0.1);
            color: var(--accent);
            border: 1px solid var(--accent-dark);
        }}

        .section-title {{
            color: white;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.1rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 5px;
        }}

        .full-details-btn {{
            display: block;
            width: calc(100% - 40px);
            margin: 20px;
            padding: 12px;
            background: var(--accent-dark);
            color: #000;
            text-align: center;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            transition: background 0.2s;
            cursor: pointer;
            border: none;
        }}

        .full-details-btn:hover {{
            background: var(--accent);
        }}

        /* Full Details Modal */
        #full-modal {{
            display: none;
            position: fixed;
            top: 5%;
            left: 5%;
            width: 90%;
            height: 90%;
            background: rgba(11, 12, 16, 0.95);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(102, 252, 241, 0.3);
            border-radius: 15px;
            z-index: 100;
            box-shadow: 0 0 30px rgba(0,0,0,0.8);
            overflow: hidden;
            flex-direction: column;
        }}

        #full-modal.show {{
            display: flex;
        }}

        .modal-header {{
            padding: 20px;
            background: rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(102, 252, 241, 0.2);
        }}

        .modal-header h1 {{ margin: 0; color: var(--accent); }}

        .modal-body {{
            padding: 20px;
            overflow-y: auto;
            flex-grow: 1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .data-card {{
            background: rgba(255,255,255,0.03);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        
        .data-row {{ margin-bottom: 8px; }}
        .data-label {{ color: #888; font-size: 0.9rem; display: inline-block; width: 150px; }}
        .data-value {{ color: #eee; }}
    </style>
</head>
<body>

    <div id="particles-js"></div>
    <div id="mynetwork"></div>

    <div id="controls">
        <button class="btn" id="btn-reset" onclick="resetSpotlight()" style="display: none;">← Reset Spotlight</button>
    </div>

    <div id="search-container">
        <input type="text" id="search-input" placeholder="Search students, skills, domains, companies..." autocomplete="off">
        <div id="search-suggestions"></div>
    </div>

    <div id="side-panel">
        <div class="panel-header">
            <h2 id="sp-name">Student Name</h2>
            <button class="close-btn" onclick="closeSidePanel()">&times;</button>
        </div>
        <div class="panel-content">
            <div class="section-title">Overview</div>
            <div style="margin-bottom: 15px;">
                <div style="color: #888; font-size: 0.9rem;">Domain</div>
                <div id="sp-domain" style="font-size: 1.1rem; text-transform: capitalize;"></div>
            </div>

            <div class="section-title">Top Skills</div>
            <div id="sp-skills"></div>

            <div class="section-title">Top Scores</div>
            <div id="sp-scores"></div>
        </div>
        <button class="full-details-btn" onclick="openFullDetails()">View Full Details →</button>
    </div>

    <div id="full-modal">
        <div class="modal-header">
            <h1 id="fm-name">Student Name</h1>
            <button class="close-btn" onclick="closeFullDetails()">&times;</button>
        </div>
        <div class="modal-body" id="fm-body">
            <!-- Populated dynamically -->
        </div>
    </div>

    <script>
        // Particles.js config for night sky
        particlesJS("particles-js", {{
            "particles": {{
                "number": {{ "value": 100, "density": {{ "enable": true, "value_area": 800 }} }},
                "color": {{ "value": "#ffffff" }},
                "shape": {{ "type": "circle" }},
                "opacity": {{ "value": 0.5, "random": true, "anim": {{ "enable": true, "speed": 1, "opacity_min": 0.1, "sync": false }} }},
                "size": {{ "value": 3, "random": true, "anim": {{ "enable": false }} }},
                "line_linked": {{ "enable": true, "distance": 150, "color": "#ffffff", "opacity": 0.1, "width": 1 }},
                "move": {{ "enable": true, "speed": 0.5, "direction": "none", "random": true, "straight": false, "out_mode": "out", "bounce": false }}
            }},
            "interactivity": {{ "detect_on": "canvas", "events": {{ "onhover": {{ "enable": true, "mode": "grab" }}, "onclick": {{ "enable": false }}, "resize": true }}, "modes": {{ "grab": {{ "distance": 140, "line_linked": {{ "opacity": 0.3 }} }} }} }},
            "retina_detect": true
        }});

        const rawStudents = {students_json};
        let currentSelectedStudent = null;
        let isSpotlightActive = false;

        // Graph Colors
        const domainColors = {{
            'backend': '#6366f1', 'machine_learning': '#f59e0b', 'vlsi_design': '#10b981', 'data_science': '#3b82f6',
            'nlp': '#8b5cf6', 'computer_vision': '#ec4899', 'embedded_systems': '#14b8a6', 'devops': '#f97316',
            'deep_learning': '#a855f7', 'cloud': '#06b6d4', 'general': '#94a3b8',
            'digital_electronics': '#059669', 'analog_circuits': '#34d399', 'signal_processing': '#6ee7b7'
        }};
        function getDomainColor(domain) {{ return domainColors[domain] || '#94a3b8'; }}

        const searchableItems = [];

        // Track Frequencies
        const domainHubs = new Set();
        const toolFrequency = {{}};
        const companyFrequency = {{}};

        // Process initial data
        rawStudents.forEach(s => {{
            domainHubs.add(s.domain);
            s.tools.forEach(t => {{ toolFrequency[t] = (toolFrequency[t] || 0) + 1; }});
            s.companies.forEach(c => {{ companyFrequency[c] = (companyFrequency[c] || 0) + 1; }});
            searchableItems.push({{ id: 'std_' + s.id, label: s.name, type: 'Student' }});
        }});

        const nodesArray = [];
        const edgesArray = [];

        // 1. Domains
        domainHubs.forEach(d => {{
            const id = 'domain_' + d;
            const label = d.toUpperCase().replace(/_/g, ' ');
            
            let count = 0;
            rawStudents.forEach(s => {{ if(s.domain === d) count++; }});
            count = count || 1;
            
            const dynamicSize = Math.min(30 + (count * 3), 70);
            const fontSize = Math.min(14 + (count * 0.5), 24);
            
            nodesArray.push({{
                id: id, label: label, shape: 'hexagon', size: dynamicSize,
                baseColor: getDomainColor(d), // Store original color
                color: {{ background: getDomainColor(d), border: '#fff' }},
                font: {{ color: '#fff', size: fontSize, bold: true }},
                group: 'domain'
            }});
            searchableItems.push({{ id: id, label: label, type: 'Domain' }});
        }});

        // 2. Tools
        Object.keys(toolFrequency).forEach(t => {{
            const count = toolFrequency[t];
            if(count >= 2) {{
                const id = 'tool_' + t;
                const dynamicSize = Math.min(15 + (count * 2), 45);
                const fontSize = Math.min(12 + (count * 0.5), 20);
                
                nodesArray.push({{
                    id: id, label: t, shape: 'diamond', size: dynamicSize,
                    baseColor: '#14b8a6',
                    color: {{ background: '#14b8a6', border: '#0d9488' }},
                    font: {{ color: '#c5c6c7', size: fontSize }},
                    group: 'tool'
                }});
                searchableItems.push({{ id: id, label: t, type: 'Tool' }});
            }}
        }});

        // 3. Companies
        Object.keys(companyFrequency).forEach(c => {{
            const count = companyFrequency[c];
            if(count >= 1) {{
                const id = 'comp_' + c;
                const dynamicSize = Math.min(15 + (count * 4), 50);
                const fontSize = Math.min(12 + count, 22);
                
                nodesArray.push({{
                    id: id, label: c, shape: 'box',
                    baseColor: '#f59e0b',
                    color: {{ background: '#f59e0b', border: '#d97706' }},
                    font: {{ color: '#000', size: fontSize, bold: true }},
                    group: 'company'
                }});
                searchableItems.push({{ id: id, label: c, type: 'Company' }});
            }}
        }});

        // 4. Students & Edges
        rawStudents.forEach(s => {{
            const stdId = 'std_' + s.id;
            nodesArray.push({{
                id: stdId, label: s.name, shape: 'dot', size: 15,
                baseColor: '#e2e8f0',
                color: {{ background: '#e2e8f0', border: '#94a3b8' }},
                font: {{ color: '#fff', size: 14 }},
                group: 'student',
                rawData: s
            }});

            // Student -> Domain Edge
            edgesArray.push({{
                id: 'edge_dom_' + s.id, from: stdId, to: 'domain_' + s.domain,
                baseColor: getDomainColor(s.domain),
                color: {{ color: 'rgba(255,255,255,0.05)', highlight: getDomainColor(s.domain) }}, 
                width: 1, hidden: true // Hidden by default to prevent mess
            }});

            // Student -> Tools Edges
            s.tools.forEach(t => {{
                if(toolFrequency[t] >= 2) {{
                    edgesArray.push({{
                        id: 'edge_tool_' + s.id + '_' + t, from: stdId, to: 'tool_' + t,
                        baseColor: '#14b8a6',
                        color: {{ color: 'rgba(255,255,255,0.05)', highlight: '#14b8a6' }}, 
                        width: 1, hidden: true, dashes: true
                    }});
                }}
            }});

            // Student -> Companies Edges
            s.companies.forEach(c => {{
                edgesArray.push({{
                    id: 'edge_comp_' + s.id + '_' + c, from: stdId, to: 'comp_' + c,
                    baseColor: '#f59e0b',
                    color: {{ color: 'rgba(255,255,255,0.05)', highlight: '#f59e0b' }}, 
                    width: 1, hidden: true
                }});
            }});
        }});

        // Initialize vis.js
        const nodesData = new vis.DataSet(nodesArray);
        const edgesData = new vis.DataSet(edgesArray);
        let network = null;

        function initNetwork() {{
            const container = document.getElementById('mynetwork');
            const data = {{ nodes: nodesData, edges: edgesData }};
            const options = {{
                nodes: {{ borderWidth: 2 }},
                edges: {{ smooth: {{ type: 'continuous' }} }},
                physics: {{
                    barnesHut: {{
                        gravitationalConstant: -4000,
                        centralGravity: 0.05,
                        springLength: 250,
                        springConstant: 0.01,
                        damping: 0.09,
                        avoidOverlap: 0.1
                    }},
                    maxVelocity: 50, solver: 'barnesHut', timestep: 0.35, stabilization: {{ iterations: 200 }}
                }},
                interaction: {{ hover: true, tooltipDelay: 200 }}
            }};

            network = new vis.Network(container, data, options);

            network.on("click", function (params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    applySpotlight(nodeId);
                }} else {{
                    resetSpotlight();
                }}
            }});
        }}

        function hexToRgba(hex, alpha) {{
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return `rgba(${{r}}, ${{g}}, ${{b}}, ${{alpha}})`;
        }}

        function applySpotlight(nodeId) {{
            isSpotlightActive = true;
            document.getElementById('btn-reset').style.display = 'block';

            const focalNode = nodesData.get(nodeId);
            if(focalNode && focalNode.group === 'student') {{
                openSidePanel(focalNode.rawData);
            }} else {{
                closeSidePanel();
            }}

            // Find connected edges and nodes
            const connectedEdgesIds = network.getConnectedEdges(nodeId);
            const connectedEdges = edgesData.get(connectedEdgesIds);
            const connectedNodesIds = new Set([nodeId]);
            
            connectedEdges.forEach(e => {{
                connectedNodesIds.add(e.from);
                connectedNodesIds.add(e.to);
            }});

            // Dim unrelated nodes, highlight related
            const updatedNodes = [];
            nodesArray.forEach(n => {{
                if(connectedNodesIds.has(n.id)) {{
                    // Highlight
                    updatedNodes.push({{
                        id: n.id,
                        color: {{ background: n.baseColor, border: '#fff' }},
                        font: {{ color: '#fff' }}
                    }});
                }} else {{
                    // Dim
                    updatedNodes.push({{
                        id: n.id,
                        color: {{ background: 'rgba(60,60,60,0.3)', border: 'rgba(60,60,60,0.1)' }},
                        font: {{ color: 'rgba(100,100,100,0.5)' }}
                    }});
                }}
            }});
            nodesData.update(updatedNodes);

            // Show relevant edges brightly, hide others
            const updatedEdges = [];
            edgesArray.forEach(e => {{
                if(e.from === nodeId || e.to === nodeId) {{
                    updatedEdges.push({{
                        id: e.id,
                        hidden: false,
                        color: {{ color: hexToRgba(e.baseColor, 0.8) }},
                        width: 2
                    }});
                }} else {{
                    updatedEdges.push({{
                        id: e.id,
                        hidden: true
                    }});
                }}
            }});
            edgesData.update(updatedEdges);
            
            // Focus camera slightly
            network.focus(nodeId, {{ scale: 1.2, animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }});
        }}

        function resetSpotlight() {{
            if(!isSpotlightActive) return;
            isSpotlightActive = false;
            document.getElementById('btn-reset').style.display = 'none';
            closeSidePanel();

            // Restore all nodes to normal
            const updatedNodes = nodesArray.map(n => ({{
                id: n.id,
                color: n.color,
                font: n.font
            }}));
            nodesData.update(updatedNodes);

            // Hide all edges again
            const updatedEdges = edgesArray.map(e => ({{
                id: e.id,
                hidden: true,
                color: e.color,
                width: 1
            }}));
            edgesData.update(updatedEdges);

            network.fit({{ animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }});
        }}

        // Search Autocomplete Logic
        const searchInput = document.getElementById('search-input');
        const suggestionsBox = document.getElementById('search-suggestions');

        searchInput.addEventListener('input', function() {{
            const val = this.value.toLowerCase().trim();
            suggestionsBox.innerHTML = '';
            
            if(!val) {{
                suggestionsBox.style.display = 'none';
                return;
            }}

            const matches = searchableItems.filter(item => item.label.toLowerCase().includes(val)).slice(0, 8);
            
            if(matches.length === 0) {{
                suggestionsBox.innerHTML = '<div class="suggestion-item" style="color:#888;">No results found</div>';
            }} else {{
                matches.forEach(match => {{
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.innerHTML = `<span>${{match.label}}</span> <span class="suggestion-type">${{match.type}}</span>`;
                    div.onclick = () => {{
                        searchInput.value = match.label;
                        suggestionsBox.style.display = 'none';
                        applySpotlight(match.id);
                    }};
                    suggestionsBox.appendChild(div);
                }});
            }}
            suggestionsBox.style.display = 'block';
        }});

        // Close suggestions on outside click
        document.addEventListener('click', function(e) {{
            if(e.target !== searchInput && e.target !== suggestionsBox) {{
                suggestionsBox.style.display = 'none';
            }}
        }});

        // UI Functions
        function openSidePanel(student) {{
            currentSelectedStudent = student;
            document.getElementById('sp-name').textContent = student.name;
            document.getElementById('sp-domain').textContent = student.domain.replace(/_/g, ' ');

            let skillsHtml = '';
            student.tools.slice(0, 10).forEach(t => {{ skillsHtml += `<span class="badge">${{t}}</span>`; }});
            if(student.tools.length > 10) skillsHtml += `<span class="badge" style="background:transparent">+${{student.tools.length - 10}} more</span>`;
            document.getElementById('sp-skills').innerHTML = skillsHtml || '<span style="color:#666">No skills listed</span>';

            let scoresHtml = '';
            const scores = Object.entries(student.scores).sort((a,b) => b[1] - a[1]).slice(0,5);
            scores.forEach(([k,v]) => {{
                let niceName = k.replace('_score', '').replace(/_/g, ' ');
                scoresHtml += `<div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span style="color:#aaa;text-transform:capitalize">${{niceName}}</span>
                    <span style="color:var(--accent);font-weight:bold">${{v}}</span>
                </div>`;
            }});
            document.getElementById('sp-scores').innerHTML = scoresHtml || '<span style="color:#666">No scores available</span>';

            document.getElementById('side-panel').classList.add('open');
        }}

        function closeSidePanel() {{
            document.getElementById('side-panel').classList.remove('open');
            currentSelectedStudent = null;
        }}

        function openFullDetails() {{
            if(!currentSelectedStudent) return;
            const data = currentSelectedStudent.full_data;
            document.getElementById('fm-name').textContent = currentSelectedStudent.name;
            
            let bodyHtml = '<div class="data-card"><h3 style="color:var(--accent); margin-top:0">Personal Info</h3>';
            const skipKeys = ['name', 'resume_filename'];
            
            for(const key in data) {{
                if(skipKeys.includes(key)) continue;
                if(data[key] === null || data[key] === '') continue;
                if(typeof data[key] === 'object') continue;
                
                let val = String(data[key]);
                if(val.length > 200) val = val.substring(0,200) + '...';
                
                bodyHtml += `<div class="data-row">
                    <span class="data-label">${{key.replace(/_/g, ' ')}}</span>
                    <span class="data-value">${{val}}</span>
                </div>`;
            }}
            bodyHtml += '</div>';

            document.getElementById('fm-body').innerHTML = bodyHtml;
            document.getElementById('full-modal').classList.add('show');
        }}

        function closeFullDetails() {{
            document.getElementById('full-modal').classList.remove('show');
        }}

        // Boot
        initNetwork();

    </script>
</body>
</html>"""

    with open(os.path.join(base_path, "knowledge_graph.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Generated knowledge_graph.html successfully with {len(students)} students in Spotlight Mode.")

if __name__ == "__main__":
    generate_html()
