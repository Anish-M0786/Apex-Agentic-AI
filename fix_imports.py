import os

base_path = r"c:\TENNUX - Agent"
code_path = os.path.join(base_path, "backend", "code")
code_tools_path = os.path.join(base_path, "backend", "code_tools")

if os.path.exists(code_path):
    os.rename(code_path, code_tools_path)
    print("Renamed directory")
else:
    print("Directory not found")

count = 0
for root, dirs, files in os.walk(os.path.join(base_path, "backend")):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = content.replace("backend.code", "backend.code_tools")
            if content != new_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {file_path}")
                count += 1
print(f"Updated {count} files in backend")

count_test = 0
for root, dirs, files in os.walk(os.path.join(base_path, "tests")):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = content.replace("backend.code", "backend.code_tools")
            if content != new_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {file_path}")
                count_test += 1
print(f"Updated {count_test} files in tests")
