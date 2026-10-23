import json
from openai import OpenAI
SYSTEM = (
   "Convert the issue into JSON with keys summary and scenarios. "
   "Each scenario must have id, criterion, steps, and verification. "
   "Each step must have action, target, and optional value. "
   "Allowed actions are fill and click. "
   "Verification must have kind and expected. "
   "Allowed verification kinds are visible_text, validation_message, completed_task. "
   "Create no more than 4 scenarios, with no more than 5 steps each. "
   "Use only criteria stated in the issue. "
   "Return a valid JSON object only, without Markdown or explanations."
)
def make_plan(issue, client:OpenAI, model:str):
    r=client.chat.completions.create(model=model,temperature=0,response_format={"type":"json_object"},messages=[
      {"role":"system","content":SYSTEM},{"role":"user","content":json.dumps({"title":issue.get("title"),"body":issue.get("body")})}])
    plan=json.loads(r.choices[0].message.content)
    if not isinstance(plan.get("scenarios"),list) or not plan["scenarios"] or len(plan["scenarios"])>4: raise ValueError("Invalid plan scenario count")
    for s in plan["scenarios"]:
      if len(s.get("steps",[]))>5: raise ValueError("Too many steps")
      for step in s["steps"]:
        if step.get("action") not in ("fill","click"): raise ValueError("Unsupported action")
    return plan
