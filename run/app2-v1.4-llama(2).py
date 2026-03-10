from flask import Flask, request, jsonify
from openai import OpenAI
from flask_cors import CORS
import yaml
import json
import re
import difflib
import jieba #pip install jieba
import random
import json
import numpy as np

app = Flask(__name__)
CORS(app)  # 允许所有来源的CORS请求

#key = open('key.txt', 'r', encoding='utf-8').read()
#client = LlamaAPI(api_key=key)


client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

class TF_IDF_Model(object):
    def __init__(self, documents_list, nodes):
        self.nodes = nodes
        self.documents_list = documents_list
        self.documents_number = len(documents_list)  # 文本总个数
        self.tf = []  # 存储每个文本中每个词的词频
        self.idf = {}  # 存储每个词汇的逆文档频率
        self.init()  # 类初始化

    def init(self):
        df = {}
        for document in self.documents_list:
            temp = {}
            for word in document:  # 存储每个文档中每个词的词频
                temp[word] = temp.get(word, 0) + 1 / len(document)
            self.tf.append(temp)
            for key in temp.keys():
                df[key] = df.get(key, 0) + 1
        for key, value in df.items():  # 每个词的逆文档频率
            self.idf[key] = np.log(self.documents_number / (value + 1))

    def get_score(self, index, query):
        score = 0.0
        for q in query:
            if q not in self.tf[index]:
                continue
            score += self.tf[index][q] * self.idf[q]
        return score

    def get_documents_score(self, query):
        score_list = {}
        for i in range(self.documents_number):
            score_list[self.nodes[i]['id']] = self.get_score(i, query)
        return score_list

def get_top_k(nodes, sorted_score, k):
    results = sorted_score[:k]
    needs_re = ""
    for i in results:
        filename = i[0]
        index_list = [index for index, data in enumerate(nodes) if data['id'] == filename][0]
        needs_re1 = f"need是【{nodes[index_list]['need']}】, 对应的yaml是【{nodes[index_list]['yaml']}】\n"
        needs_re += needs_re1
    return needs_re


@app.route('/spec', methods=['POST'])
def spec():
    # 从请求中获取 JSON 数据
    data = request.get_json()
    # 从 JSON 数据中提取问题
    question = data['question']
    print("need内容为"+question)
    prompt = open('./promptspec.txt', 'r', encoding='utf-8').read()
    messages = [
        {
            "role": "system",
            "content": prompt+"所需要生成的need是:"},
        {
            "role": "user",
            "content": question
        }
    ]
    chat_completion = client.chat.completions.create(
        model="meta/llama-3.1-70b-instruct",
        messages=messages,
        temperature=0.9,
        top_p=0.7,
        max_tokens=1024,
        stream=False
    )
    spec = chat_completion.choices[0].message.content
    print("spec内容为"+spec)
    return jsonify({'spec':spec})


@app.route('/ask', methods=['POST'])
def ask():
    # 从请求中获取 JSON 数据
    data = request.get_json()
    # 从 JSON 数据中提取问题
    question = data['question']
    answer1_filepath = '.\extracted_data_cleaned.json'  # 替换为实际的语料库文件地址
    with open(answer1_filepath, 'r', encoding='utf-8') as file:
        nodes = json.load(file)

    # 所有分词
    document_list = [list(jieba.cut(node['need'])) for node in nodes if 'need' in node and isinstance(node['need'], str)]
    tf_idf_model = TF_IDF_Model(document_list, nodes)
    while True:
        data1 = random.sample(nodes, 1)[0]  # 抽取一个随机样本
        data1_filename = data1['yaml']
        data1_need = data1['need']
        if data1_need != '':
            break

    query = list(jieba.cut(question))
    scores = tf_idf_model.get_documents_score(query)
    sorted_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = get_top_k(nodes, sorted_score, 3)
    combined_responses = []
    combined_answer = []
    # print(f'needs是：{data1_need}')
    #print(results)
    for _ in range(3):
    # 定义一个 messages 列表，包含一个 "system" 角色的消息和一个 "user" 角色的消息
        prompt = open('./prompt.txt', 'r', encoding='utf-8').read()
        messages = [
            {
                "role": "system",
                "content": prompt+results[_]+"所需要生成的任务是:"},
            {
                "role": "user",
                "content": question
            }
        ]

        # 打印问题
        print(question)
        answer, response = get_response(client, messages,_)
        print(answer)
        combined_responses.append(response)
        combined_answer.append(answer)





        '''
        prompt = open('./prompt.txt', 'r', encoding='utf-8').read()
        messages = [
            {
                "role": "system",
                "content": prompt+results+"所需要生成的need是:"},
            {
                "role": "user",
                "content": question
            }
        ]
        combined_responses2, combined_answer2 = process_chat_completion(client, messages)###
        '''




    return jsonify({"answer": combined_responses, "yaml_answer": combined_answer})

def get_response(client, messages,n):
    chat_completion = client.chat.completions.create(
        model="meta/llama-3.1-70b-instruct",
        messages=messages,
        temperature=0.9,
        top_p=0.7,
        max_tokens=5012,
        stream=False
        )
    answer = chat_completion.choices[0].message.content
    yaml_content = extract_yaml_from_answer(answer)
    response = yaml_to_json(yaml_content,n)
    return answer, response


@app.route('/jsonload', methods=['POST'])
def jsonload():
    # 读取第一个文件
    with open('./componentsALL-2.json', 'r', encoding='utf-8') as f1:
        keyjson1 = json.load(f1)
    
    # 读取第二个文件
    with open('./uikit.json', 'r', encoding='utf-8') as f2:
        keyjson2 = json.load(f2)
    
    # 返回两个文件的内容
    return jsonify({'file1': keyjson1, 'file2': keyjson2})

@app.route('/updateyaml', methods=['POST'])
def update_yaml():
    # 从请求中获取新的 YAML 数据
    data = request.get_json()
    yaml_content = data['yaml_content']
    number_yaml=data['n']

    # 将 YAML 转换为 JSON
    new_json = yaml_to_json(yaml_content,number_yaml)

    # 返回生成的 JSON 数据
    return jsonify({"updated_json": new_json})



def extract_yaml_from_answer(answer):
    # 提取出markdown形式的yaml代码块
    yaml_match = re.search(r'```(.*?)```', answer, re.DOTALL)
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

def process_yaml(original_str):
    # Split the string into lines
    original_str = original_str.replace("\n\n", "\n")
    lines = original_str.strip().split('\n')

    # Store the converted lines
    converted_lines = []
    multiline_value = []

    for line in lines:
        if re.match(r'\s*-\s*\w+:', line):
            # If it's in the "-key:" format, remove the "-"
            if multiline_value and converted_lines:
                # If there's a multiline value being accumulated, join and add it before processing the next key
                converted_lines[-1] += ', '.join(multiline_value)
                multiline_value = []
            line = re.sub(r'-\s*', '', line)
            converted_lines.append(line)
        elif re.match(r'\s*\w+', line) and not re.match(r'\s*\w+:', line):
            # If it's a multiline value (not starting with "-key:" or "key:"), accumulate the value
            value = line.strip()
            multiline_value.append(value)
        elif re.match(r'\s*-\s*[^:]+', line):
            # If it's in the "- value" format, remove the "-" and append the value to the previous line
            value = re.sub(r'-\s*', '', line).strip()
            if converted_lines:
                converted_lines[-1] += f', {value}'
            else:
                # Handle case where converted_lines is empty
                converted_lines.append(value)
        else:
            # Otherwise, just add the line
            if multiline_value and converted_lines:
                converted_lines[-1] += ', '.join(multiline_value)
                multiline_value = []
            if line.strip():  # Ensure that the line is not empty
                converted_lines.append(line)

    # If there's any leftover multiline value at the end, add it
    if multiline_value and converted_lines:
        converted_lines[-1] += ', '.join(multiline_value)

    # Join the lines back into a single string
    converted_str = '\n'.join(converted_lines)
    converted_str = re.sub(r':\s*,', ':', converted_str)

    return converted_str

def restructure_yaml(yaml_str):
    input_yaml = yaml_str
    yaml_str = process_yaml(input_yaml)
    lines = yaml_str.strip().split('\n')
    result = []
    stack = []
    current_level = -1

    for line in lines:
        stripped = line.lstrip()
        indent_level = len(line) - len(stripped)
        is_list_item = stripped.startswith('-')

        if is_list_item:
            stripped = stripped[1:].lstrip()

        entry = stripped.split(':', 1)
        key = entry[0].strip()
        value = entry[1].strip() if len(entry) > 1 else None

        if value:
            value = value.split(', ')
            value = value[0] if len(value) == 1 else ', '.join(value)

        while stack and stack[-1][1] >= indent_level:
            stack.pop()

        new_entry = {key: value} if value else {key: []}

        if stack:
            parent = stack[-1][0]
            if isinstance(parent, dict):
                if isinstance(parent[key], list):
                    parent[key].append(new_entry)
                else:
                    parent[key] = [new_entry]
            elif isinstance(parent, list):
                parent.append(new_entry)
        else:
            result.append(new_entry)

        if not value:
            stack.append((new_entry[key], indent_level))

    return result


def remove_nulls(obj):
    if isinstance(obj, dict):
        return {k: remove_nulls(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [remove_nulls(v) for v in obj if v is not None]
    else:
        return obj

# Convert the YAML-like structure to the required JSON format
def is_special_key(key):
    special_keys = {"header", "body", "rightsider", "leftsider", "footer"}
    return key.lower() in special_keys


def determine_type(name, content, child, level=1):
    name_lower = name.lower()
    type_mapping = {
        "radiobutton": "radio",
        "tab": "nonant-tab",
        "navmenu": "Navigation-menu",
        "avatar": "nonant-Avatar",
        "card": "Card-box",
        "table": "table-body",
        "list": "Size=medium, Header=true, Footer=false, Load More=true",
        "breadcrumb": "nonant-Breadcrumb",
        "sidenavigation": "nonant-sidenavigation",
        "pagination": "Size=medium, Total-text=true, State=normal",
        "timeline": "Timeline.Item/Left",
        "steps": "Item Count=3, Direction=horizontal, Size=medium, Description=true",
        "progress": "Components/Table-Cell/Progress",
        "input": "Size=medium, State=normal, Show Count=false, Filled=false",
        "search": "Size=medium, Enter=icon, Suffix=false, Filled=false, Allow Clear=false",
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
        "alert": "Alert",
        "title": "nonant-title"
    }

    if name_lower in type_mapping:
        return type_mapping[name_lower]

    if name_lower == "button":
        if "http" in content.lower():
            return "Type=link, Shape=standard, Size=medium, State=normal, Danger=false, Ghost=false"
        if level == 1:
            return "Type=primary, Shape=standard, Size=medium, State=normal, Danger=false, Ghost=false"
        return "Type=secondary, Shape=standard, Size=medium, State=normal, Danger=false, Ghost=false"

    if name_lower == "form":

        button_in_child = any(childs.get("name", "").lower() == "button" for childs in child)
        input_in_child = any(childs.get("name", "").lower() == "input" for childs in child)
        item_in_child = any(childs.get("name", "").lower() == "item" for childs in child)
        select_in_child = any(childs.get("name", "").lower() == "select" for childs in child)

        if not (button_in_child or input_in_child or item_in_child or select_in_child):
            return f"Layout=horizontal, Size=medium, Items={content.count(',') + 1}, Button=false"
        if button_in_child:
            return f"Layout=horizontal, Size=medium, Items={content.count(',') + 1}, Button=true"
        if input_in_child:
            return "Status=normal, Required=false, Optional=false, Tooltip=false, Help Text=false"
        if item_in_child or select_in_child:
            return "Status=normal, Required=false, Optional=false, Tooltip=false, Help Text=false"

    if name_lower == "dropdown":
        return f"dropdownstatus=close"

    if name_lower == "collapse":
        #return f"Item Count={content.count(',') + 1}, Borderless=false"
        return f"nonant-Collapse"

    if name_lower == "select":
        if "," in content:
            return f"Size=medium, Filled=true, MultiSelect=true, ⬑Custom Tag=false, Disabled=false, Open=false, Hovering=false"
        return f"Size=medium, Filled=true, MultiSelect=false, ⬑Custom Tag=false, Disabled=false, Open=false, Hovering=false"

    if name_lower == "text":
        if "http" in content.lower():
            return "Hierarchy=link, Bullet=false, Editable=false, Copyable=false"
        return "Hierarchy=primary, Bullet=false, Editable=false, Copyable=false"

    if name_lower == "header":
        return "header"
    if name_lower == "leftsider":
        return "leftsider"
    if name_lower == "body":
        return "body"
    if name_lower == "footer":
        return "footer"
    if name_lower == "rightsider":
        return "rightsider"

    return "unknown"


def yaml_to_json(yaml_str,n):
    if yaml_str.startswith("```yaml"):
        yaml_str = yaml_str.strip("```yaml").strip("```")
    output = restructure_yaml(yaml_str)
    output_yaml = yaml.dump(output, allow_unicode=True, default_flow_style=False)

    try:
        yaml_obj = yaml.safe_load(output_yaml)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return {}

    def convert_to_json(data, x=0, y=0):
        result = []
        for item in data:
            for key, value in item.items():
                node = {
                    "name": key.lower(),
                    "content": "",
                    "bbox": {"x": x, "y": y},
                    "child": []
                }
                if isinstance(value, list):
                    node["child"] = convert_to_json(value, x, y)
                elif isinstance(value, dict):
                    node["content"] = ''
                    node["child"] = convert_to_json([value], x, y)
                else:
                    node["content"] = value
                result.append(node)
        return result

    json_result = {
        "page": [convert_to_json([item])[0] for item in yaml_obj if is_special_key(list(item.keys())[0])]
    }
    valid_names = [ "button", "avatar", "card", "form", "table", "list", "collapse", "navmenu", "dropdown", "breadcrumb",
                    "sidenavigation", "tree", "tab", "pagination", "timeline", "steps", "progress", "input", "search",
                    "select", "datepicker", "timepicker", "switch", "slider", "checkbox", "radio", "fileupload",
                    "imageupload", "linechart", "piechart", "areachart", "gaugechart", "barchart", "text", "title",
                    "header", "body", "rightsider", "leftsider", "footer" ]

    def closest_match(name, valid_names):
        """返回与name最相似的名字"""
        matches = difflib.get_close_matches(name, valid_names, n=1, cutoff=0.6)
        return matches[0] if matches else name

    def update_json_names(data):
        """更新json数据中的name字段"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "name" and value not in valid_names:
                    closest_name = closest_match(value, valid_names)
                    data[key] = closest_name
                else:
                    update_json_names(value)
        elif isinstance(data, list):
            for item in data:
                update_json_names(item)

    def handle_list_to_card(data):
        """将name为list且child不为空且包含text之外的组件转换为card"""
        if isinstance(data, dict):
            if data.get("name") == "list":
                if "child" in data and isinstance(data["child"], list):
                    contains_non_text = any(child.get("name") != "text" for child in data["child"])
                    if contains_non_text:
                        data["name"] = "card"
            for key, value in data.items():
                handle_list_to_card(value)
        elif isinstance(data, list):
            for item in data:
                handle_list_to_card(item)

    def handle_item_to_card(data):
        """将name为item或items的转换为card"""
        if isinstance(data, dict):
            if data.get("name") in ["item", "items"]:
                data["name"] = "card"
            for key, value in data.items():
                handle_item_to_card(value)
        elif isinstance(data, list):
            for item in data:
                handle_item_to_card(item)

    def merge_text_content(data):
        """将text的content添加到其父组件的content中"""
        if isinstance(data, dict):
            if data.get("name") not in ["header", "body", "footer", "card"]:
                text_contents = []
                new_children = []
                for child in data.get("child", []):
                    if child.get("name") == "text":
                        text_contents.append(child.get("content", ""))
                    else:
                        new_children.append(child)
                data["child"] = new_children
                if text_contents:
                    data["content"] += " ".join(text_contents)
            for key, value in data.items():
                merge_text_content(value)
        elif isinstance(data, list):
            for item in data:
                merge_text_content(item)

    update_json_names(json_result)
    handle_list_to_card(json_result)
    handle_item_to_card(json_result)

    # 在类型添加之前进行text content的合并
    merge_text_content(json_result)

    def add_type_to_json(data, level=1):
        for node in data:
            name = node["name"].lower()
            content = node.get("content", "")
            child = node.get("child", [])
            node["type"] = determine_type(name, content, child, level)
            if "child" in node and node["child"]:
                add_type_to_json(node["child"], level + 1)
        return data

    json_result_with_type = {
        "type":"Landing Page",
        "name":f"Landing Page{n}",
        "bbox":{"x":n*2000,"y":0},
        "child":add_type_to_json(json_result["page"])
    }

    def update_footer_table_type(data):
        if isinstance(data, dict):
            if data.get("name") == "footer":
                for child in data.get("child", []):
                    # 只转换 "table" 组件的 type
                    if child.get("name") == "table":
                        child["type"] = "table-footer"
            for key, value in data.items():
                update_footer_table_type(value)
        elif isinstance(data, list):
            for item in data:
                update_footer_table_type(item)

    update_footer_table_type(json_result_with_type)
    json_result1 = json.dumps(json_result_with_type, ensure_ascii=False, indent=4)
    return json_result1



# 修改后的类型转换函数


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
