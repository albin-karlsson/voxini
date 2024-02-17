#def get_geo_node():
#    # Get the current pane tabs
#    pane_tabs = hou.ui.currentPaneTabs()
#    
#    # Iterate over the pane tabs to find the Scene Viewer
#    for pane_tab in pane_tabs:
#        if isinstance(pane_tab, hou.SceneViewer):
#            # Get the current item from the scene viewer
#            current_item = pane_tab.currentNode()
#            
#            # Check if the current item is a SOP node (geometry object)
#            if current_item and isinstance(current_item, hou.SopNode):
#                # Get the parent geo node
#                geo_node = current_item.parent()
#                
#                return geo_node
#            else:
#                geo_nodes = hou.node("/obj").children()
#                
#                if len(geo_nodes) == 1:
#                    existing_geo_node = geo_nodes[0]
#                    
#                    return existing_geo_node
#                else:
#                    new_geo_node = hou.node("/obj").createNode("geo")
#                    
#                    return new_geo_node

from openai import OpenAI
import re
import hou

def generate(kwargs):
    # Get prompt parameter
    prompt = kwargs["node"].parm("prompt").eval()
    
    if prompt != "":
        client = OpenAI()
        generator = HoudiniCodeGenerator(client)
        generator.set_base_prompt(prompt)
        
        if kwargs["node"].parm("save_script").eval():
            filepath = kwargs["node"].parm("filepath").eval()
            
            if filepath:
                generator.set_filepath(filepath)
            else:
                print("No filepath specified. . .")
                return
            
            generator.set_save_script()      
        
        generator.make_call()

class HoudiniCodeGenerator:
    def __init__(self, client):
        self.client = client
        self.base_prompt = ""
        self.save_script = False
        self.filepath = ""
        self.tries = 0
        self.error = ""

    def set_base_prompt(self, prompt):
        self.base_prompt = prompt
        
    def set_save_script(self):
        self.save_script = True
        
    def set_filepath(self, filepath):
        self.filepath = filepath

    def make_call(self):
        if self.tries >= 5:
            print("Maximum retry attempts reached.")
            return

        system_message = (
            "Generate Python code in a code block optimized for seamless integration within Houdini. "
            "Ensure the output adheres strictly to Houdini's environment and API specifications. "
            "The code should revolve around a single geometry (geo) as the container for all elements. "
            "Organize the nodes logically and establish coherent connections to uphold clarity and functionality. "
            "Set the display and render flags to the last object in the node chain or the object that logically should have them."
        )

        if self.error:
            user_prompt = f"Previous attempt resulted in an error: {self.error}. Adjust the following code to prevent this issue.\n\n{self.base_prompt}"
        else:
            user_prompt = self.base_prompt

        completion = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = completion.choices[0].message.content
        formatted_content = self.format_content(content)

        if formatted_content:
            self.try_run_code(formatted_content)
        else:
            print("Could not format content. Try again...")

    def format_content(self, content):
        pattern = r"```python\n(.*?)\n```"
        matches = re.search(pattern, content, re.DOTALL)

        if matches:
            formatted_content = matches.group(1)  # Extracted code part

            # Process the content (e.g., remove unwanted lines, add necessary imports)

            if "import hou" not in formatted_content:
                formatted_content = "import hou\n" + formatted_content

            return formatted_content
        else:
            return None

    def try_run_code(self, code):
        hou.undos.clear()

        try:
            exec(code, globals(), locals())
            # hou.undos.group does not work in a callback script
#            with hou.undos.group("Executing code block"):
#                exec(code, globals(), locals())
        except Exception as e:
#            hou.undos.performUndo()
            error_message = f"{type(e).__name__}: {e}"
            print(f"Attempt {self.tries + 1}: Error executing code - {error_message}")

            self.error = error_message
            self.tries += 1
            self.make_call()
        else:
            print(f"Code executed successfully.")
            
            if self.save_script and self.filepath:
                with open(self.filepath, 'w') as file:
                    # Write the string containing your Python code to the file
                    file.write(code)
                
                print(f"Python script saved to {self.filepath}")
                                        
            # Reset tries and error for future calls
            self.tries = 0
            self.error = ""