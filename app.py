from flask import Flask, render_template_string
app = Flask(__name__)
PAGE = r'''
<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Task Manager</title>
<style>body{font-family:system-ui;max-width:700px;margin:50px auto;padding:0 20px}form{display:flex;gap:8px}input{flex:1;padding:12px}button{padding:10px;cursor:pointer}.completed .task-name{text-decoration:line-through;color:#64748b}.message{color:#b91c1c;min-height:24px}</style></head>
<body><h1>Task Manager</h1><form id="task-form"><label for="task-input" style="position:absolute;left:-9999px">Task name</label><input id="task-input" placeholder="Enter a task"><button type="submit">Add task</button></form>
<p id="message" class="message" role="status" aria-live="polite"></p><h2>Your tasks</h2><ul id="task-list" aria-label="Task list"></ul>
<script>
const tasks=[];const form=document.querySelector('#task-form'),input=document.querySelector('#task-input'),message=document.querySelector('#message'),list=document.querySelector('#task-list');
function render() {
   list.replaceChildren();
   tasks.forEach((task, index) => {
       const li = document.createElement('li');
       if (task.completed) {
           li.classList.add('completed');
       }
       const name = document.createElement('span');
       name.className = 'task-name';
       name.textContent = task.name;
       li.appendChild(name);
       const button = document.createElement('button');
       button.type = 'button';
button.id = `completeTask-${index + 1}`;
       button.textContent = task.completed
           ? 'Completed'
           : 'Mark complete';
       button.setAttribute(
           'aria-label',
           (task.completed ? 'Completed ' : 'Mark complete ') + task.name
       );
       button.disabled = task.completed;
       button.onclick = () => {
           task.completed = true;
           message.textContent = '';
           render();
       };
       li.appendChild(button);
       list.appendChild(li);
   });
}
form.onsubmit=e=>{e.preventDefault();const name=input.value.trim();if(!name){message.textContent='Please enter a task name.';return}tasks.push({name,completed:false});input.value='';message.textContent='Task added.';render()};
</script></body></html>'''
@app.get("/")
def index(): return render_template_string(PAGE)
@app.get("/health")
def health(): return {"status":"ok"}
if __name__ == "__main__": app.run(host="127.0.0.1", port=5000, debug=False)
