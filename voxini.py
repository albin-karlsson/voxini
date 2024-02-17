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

class HoudiniCodeGenerator:
    def __init__(self, client):
        self.client = client
        self.base_prompt = ""
        self.tries = 0
        self.error = ""

    def set_base_prompt(self, prompt):
        self.base_prompt = prompt

    def make_call(self):
        if self.tries >= 5:
            print("Maximum retry attempts reached.")
            return

        system_message = (
            "Generate Python code in a code block tagged as Python code optimized for seamless integration within Houdini using its API. "
            "Ensure the output adheres strictly to Houdini's environment and API specifications. "
            "The generated code should revolve around a single geometry (geo) variable named 'geo_node' "
            "as the central container for all elements. Organize the nodes logically and establish "
            "coherent connections to uphold clarity and functionality. Remember to set the display "
            "and render flags appropriately, typically to the last object in the node chain or the "
            "object that logically should have them."
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
            # This part remains as in your original function

            return formatted_content
        else:
            return None

    def try_run_code(self, code):
        hou.undos.clear()

        try:
            with hou.undos.group("Executing code block"):
                exec(code, globals(), locals())
        except Exception as e:
            hou.undos.performUndo()
            error_message = f"{type(e).__name__}: {e}"
            print(f"Attempt {self.tries + 1}: Error executing code - {error_message}")

            self.error = error_message
            self.tries += 1
            self.make_call()
        else:
            print(f"Code executed successfully.")
            # Reset tries and error for future calls
            self.tries = 0
            self.error = ""

# Usage example
client = OpenAI()  # Ensure you have initialized the OpenAI client correctly
generator = HoudiniCodeGenerator(client)
generator.set_base_prompt("Create 5 different spheres of different sizes. Merge them all together and put a bounding box around all of them.")
generator.make_call()