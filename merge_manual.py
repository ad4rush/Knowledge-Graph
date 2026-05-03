import os, json, glob

def merge_manual_data():
    manual_files = glob.glob('manual_text/*.json')
    output_files = glob.glob('output/*.json')
    
    # Create mapping of name -> output_file
    output_map = {}
    for of in output_files:
        with open(of, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if 'name' in data and data['name']:
                    output_map[data['name'].lower()] = of
                # Also index by filename as fallback
                basename = os.path.basename(of).replace('.json', '').lower()
                output_map[basename] = of
            except:
                pass

    merged_count = 0
    for mf in manual_files:
        with open(mf, 'r', encoding='utf-8') as f:
            try:
                mdata = json.load(f)
            except:
                continue
        
        name = mdata.get('student_name', '').lower()
        basename = os.path.basename(mf).replace('.json', '').lower()
        
        target_file = output_map.get(name) or output_map.get(basename)
        
        if target_file:
            with open(target_file, 'r', encoding='utf-8') as f:
                odata = json.load(f)
            
            # Merge logic
            changed = False
            # Append manual skills to net_tools_technologies
            manual_skills = mdata.get('skills')
            if manual_skills:
                clean_skills = "; ".join([s.strip() for s in manual_skills.split('\n') if s.strip()])
                existing_tools = odata.get('net_tools_technologies') or ''
                if clean_skills not in existing_tools:
                    if existing_tools:
                        odata['net_tools_technologies'] = existing_tools + "; " + clean_skills
                    else:
                        odata['net_tools_technologies'] = clean_skills
                    changed = True
            
            # Append manual courses
            manual_courses = mdata.get('courses')
            if manual_courses:
                clean_courses = "; ".join([s.strip() for s in manual_courses.split('\n') if s.strip()])
                existing_courses = odata.get('relevant_coursework') or ''
                if clean_courses not in existing_courses:
                    if existing_courses:
                        odata['relevant_coursework'] = existing_courses + "; " + clean_courses
                    else:
                        odata['relevant_coursework'] = clean_courses
                    changed = True
            
            # Append manual projects
            manual_projects = mdata.get('projects')
            if manual_projects and isinstance(manual_projects, dict):
                raw_proj = manual_projects.get('raw_text', '')
                if raw_proj:
                    # Find empty slot
                    for i in range(1, 9):
                        title = odata.get(f'project_{i}_title')
                        if not title:
                            odata[f'project_{i}_title'] = 'Additional Verified Projects'
                            odata[f'project_{i}_description'] = raw_proj[:800].replace('\n', ' ')
                            changed = True
                            break
                        elif title == 'Additional Verified Projects':
                            break # already added
            
            if changed:
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(odata, f, indent=2, ensure_ascii=False)
                print(f"Merged manual data for {name or basename}")
                merged_count += 1

    print(f"Total merged: {merged_count}")

if __name__ == '__main__':
    merge_manual_data()
