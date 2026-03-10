import yaml
import json
import re



def extract_yaml_from_answer(answer):
    # 提取出markdown形式的yaml代码块
    yaml_match = re.search(r'```yaml(.*?)```', answer, re.DOTALL)
    if yaml_match:
        return yaml_match.group(1).strip()
    else:
        # 也处理没有markdown形式的yaml代码
        yaml_lines = []
        in_yaml = False
        for line in answer.split('\n'):
            if re.match(r'^\s*\w+:', line):
                in_yaml = True
            if in_yaml:
                yaml_lines.append(line)
        return '\n'.join(yaml_lines).strip() if yaml_lines else None
    

