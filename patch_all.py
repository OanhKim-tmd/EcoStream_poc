import os
import re

def patch_server():
    p = '/home/oanh/cccccccccccccc/ecostream/app/server.py'
    with open(p, 'r', encoding='utf-8') as f: content = f.read()

    # 1. Change orch initialization
    old_init = "orch = WorkflowOrchestrator(offline_mode=True)"
    new_init = """import re
        safe_c = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]+', '-', company).strip('-')
        safe_l = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]+', '-', location).strip('-')
        from datetime import datetime
        ts_suffix = datetime.now().strftime("%H%M%S")
        run_name = f"{safe_c}_{safe_l}_{period}_{ts_suffix}"
        orch = WorkflowOrchestrator(run_id=run_name, offline_mode=True)"""
    
    if old_init in content:
        content = content.replace(old_init, new_init)
    
    # 2. Remove markdown and HTML export routes
    content = re.sub(r'@app\.get\("/api/export/markdown".*?return PlainTextResponse\([^)]+\)', '', content, flags=re.DOTALL)
    content = re.sub(r'@app\.get\("/api/export/html".*?return HTMLResponse\([^)]+\)', '', content, flags=re.DOTALL)
    
    with open(p, 'w', encoding='utf-8') as f: f.write(content)


def patch_pipeline():
    p = '/home/oanh/cccccccccccccc/ecostream/orchestrator/pipeline.py'
    with open(p, 'r', encoding='utf-8') as f: content = f.read()
    
    # Remove HTML/MD deliverable generation
    content = re.sub(r'# Markdown Report.*?html_path = os\.path\.join\(deliv_dir, "Bao_cao_kiem_ke_va_giam_nhe_KNK\.html"\)\n\s+with open\(html_path, "w", encoding="utf-8"\) as f:\n\s+f\.write\(html_content\)', '', content, flags=re.DOTALL)
    
    # In deliverables dictionary, remove missing paths
    content = content.replace('"markdown": md_path,', '')
    content = content.replace('"html": html_path,', '')
    
    with open(p, 'w', encoding='utf-8') as f: f.write(content)

patch_server()
patch_pipeline()
print("Patched server and pipeline")
