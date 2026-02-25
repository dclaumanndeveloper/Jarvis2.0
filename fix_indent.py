with open('services/optimized_voice_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
start = False
for line in lines:
    if "# Check if we've had enough silence" in line:
        start = True
    
    if start:
        if "except queue.Empty:" in line:
            start = False
            new_lines.append(line)
            continue
            
        if line.startswith("                            "):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open('services/optimized_voice_service.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Indentation fixed.")
