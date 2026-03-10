import yaml
import json

def process_type(type_name, content, nested_level):
    type_name_lower = type_name.lower()
    if isinstance(content, str):
        content_items_count = len(content.split(','))
    elif isinstance(content, list):
        content_items_count = len(content)
    else:
        content_items_count = 0

    type_mapping = {
        "radiobutton": "radio",
        "tag": "tab",
        "nav menu": "sideNavigation",
        "header": "Breadcrumb=false, Extra=true, Content=false, Tabs=false",
        "sider": "Sub Menus=true, Contracted=false",
        "button": f"X, Shape=standard, Size=medium, State=normal, Danger=false, Ghost=false",
        "avatar": "Avatar",
        "card": "Size=medium, Bordered=true, Head=false, Cover=true, Actions=false",
        "form": f"Layout=horizontal, Size=medium, X",
        "table": "Layout=horizontal, Size=medium, Items=2, Button=true",
        "list": "Size=medium, Header=true, Footer=false, Load More=true",
        "collapse": f"X, Borderless=false",
        "dropdown": f"Arrow=no arrow, X",
        "breadcrumb": "BreadCrumb",
        "sidenavigation": "Selected=true, Submenu=true, ⬑Open=true",
        "pagination": "Size=medium, Total-text=true, State=normal",
        "timeline": "Timeline.Item/Left",
        "steps": "Components/Steps-Item-Icon",
        "progress": "Components/Table-Cell/Progress",
        "input": "Size=medium, State=normal, Show Count=false, Filled=false",
        "search": "Size=medium, Enter=icon, Suffix=false, Filled=false, Allow Clear=false",
        "select": f"Size=medium, Filled=true, X, ⬑Custom Tag=false, Disabled=false, Open=false, Hovering=false",
        "datepicker": "Size=medium, Filled=true,Ranged=true",
        "timepicker": "Size=medium, Filled=true, Ranged=true, Disabled=false",
        "slider": "Range=true, Icon=false, Marks=true",
        "checkbox": "Checked=true, Indeterminate=false, Disable=false, Hovering=false, Label=true",
        "switch": "Size=medium, Checked=true, Text=false, Icon=false, Loading=false, Disabled=false, Animation=false",
        "linechart": "lineChart",
        "radarchart": "RadarChart",
        "piechart": "pieChart",
        "areachart": "areaChart",
        "barchart": "BarChart",
        "radio": "Components/Radio",
        "fileupload": "Upload-Drag",
        "imageupload": "Uploaded=true, Type=picture",
        "text": f"Hierarchy=primary, Bullet=false, Editable=false, Copyable=false",
        "alert": "Alert",
        "title": "Badge=off, Icon=off, Subtitle=off, Tabs=off, Dropdown=off",
        "unknown": "unknown"
    }

    if type_name_lower in type_mapping:
        type_value = type_mapping[type_name_lower]
        if "X" in type_value:
            if type_name_lower == "button":
                if "href" in content.lower():
                    type_value = type_value.replace("X", "Type=link")
                elif nested_level > 0:
                    type_value = type_value.replace("X", "Type=secondary")
                else:
                    type_value = type_value.replace("X", "Type=primary")
            elif type_name_lower in ["collapse", "dropdown", "select"]:
                type_value = type_value.replace("X", f"Items={content_items_count}")
            elif type_name_lower == "text":
                if "href" in content.lower():
                    type_value = type_value.replace("X", "Hierarchy=link")
                else:
                    type_value = type_value.replace("X", "Hierarchy=primary")
            elif type_name_lower == "form":
                if isinstance(content, str):
                    type_value = type_value.replace("X", f"Items={content_items_count}")
                if isinstance(content, dict):
                    child_types = [child.lower() for child in content.keys()]
                    if "button" in child_types:
                        type_value = type_value.replace("X", f"Items={content_items_count}, Button=true")
                    elif any(item in child_types for item in ["input", "item", "select"]):
                        type_value = type_value.replace("X", f"Items={content_items_count}, Button=false")
                        if "input" in child_types:
                            type_value += ", Status=normal, Required=false, Optional=false, Tooltip=false, Help Text=false"
                        if any(item in child_types for item in ["item", "select"]):
                            type_value += ", Status=normal, Required=false, Optional=false, Tooltip=false, Help Text=false"
    else:
        type_value = "unknown"

    return type_value

def convert_to_list_format(yaml_str):
    lines = yaml_str.splitlines()
    new_lines = []
    parent_key = None

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if not line.startswith("  ") and not line.startswith("- "):
            parent_key = stripped_line.split(":")[0]
            new_lines.append(line)
        elif line.startswith("  "):
            if parent_key and not new_lines[-1].strip().startswith("- "):
                new_lines.append(f"  - {line.strip()}")
            else:
                new_lines.append(f"    {line.strip()}")
        else:
            new_lines.append(line)

    return "\n".join(new_lines)

def yaml_to_json(yaml_str):
    yaml_str = convert_to_list_format(yaml_str)

    try:
        yaml_obj = yaml.safe_load(yaml_str)
        print(yaml_obj)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return {}

    json_obj = []
    valid_first_level_keys = {"header", "body", "rightsider", "leftsider", "footer"}
    valid_first_level_keys_lower = {key.lower() for key in valid_first_level_keys}
    bbox_y = 0

    def process_node(name, content, is_first_level=False, nested_level=0):
        nonlocal bbox_y
        name_lower = name.lower()
        node = {
            "name": name if is_first_level else None,
            "type": process_type(name_lower, content, nested_level) if not is_first_level else None,
            "content": "",
            "bbox": {"x": 0, "y": bbox_y},
            "child": []
        }

        if isinstance(content, dict):
            for key, value in content.items():
                if key.lower() == "text":
                    node["child"].append({
                        "type": process_type("text", value, nested_level + 1),
                        "content": value,
                        "bbox": {"x": 0, "y": 0},
                        "child": []
                    })
                else:
                    children = process_multiple_nodes(key, value, nested_level=nested_level + 1)
                    node["child"].extend(children)
            bbox_y += 10
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    for key, value in item.items():
                        children = process_multiple_nodes(key, value, nested_level=nested_level + 1)
                        node["child"].extend(children)
                else:
                    node["child"].append({
                        "type": process_type(name.lower(), item, nested_level + 1),
                        "content": item,
                        "bbox": {"x": 0, "y": 0},
                        "child": []
                    })
            bbox_y += 10
        elif isinstance(content, str):
            node["content"] = content
        else:
            return None

        if is_first_level:
            del node["type"]
        else:
            del node["name"]

        return node

    def process_multiple_nodes(name, content, is_first_level=False, nested_level=0):
        if isinstance(content, list):
            nodes = []
            for item in content:
                nodes.append(process_node(name, item, is_first_level, nested_level))
            return nodes
        elif isinstance(content, dict):
            nodes = []
            for key, value in content.items():
                nodes.append(process_node(key, value, nested_level=nested_level))
            return nodes
        else:
            return [process_node(name, content, is_first_level, nested_level)]

    for key, value in yaml_obj.items():
        if key.lower() in valid_first_level_keys_lower:
            nodes = process_multiple_nodes(key, value, is_first_level=True)
            json_obj.extend(nodes)

    page_structure = {"page": []}
    for key, value in yaml_obj.items():
        if key.lower() in valid_first_level_keys_lower:
            node = process_node(key, value, is_first_level=True)
            page_structure["page"].append(node)

    return json.dumps(page_structure, ensure_ascii=False, indent=2)

# 示例YAML字符串
yaml_str = """
Header: 
  text: Smart智能AI数据分析控制台
  search: 搜索
  dropdown: 脚本生成, 运营数据, AW管理
LeftSider: 
  sideNavigation: 业务准确率, 用户访问数据, AW统计信息
Body:
  card:
    text: 业务准确率
  card:
    text: 用户访问数据
  card:
    text: AW统计信息
  button: 我
"""

# 调用函数并转换类型
response = yaml_to_json(yaml_str)
json_output = json.loads(response)

# 打印最终结果
final_json_output = json.dumps(json_output, ensure_ascii=False, indent=2)
print(final_json_output)

