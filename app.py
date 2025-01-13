from flask import Flask, request, jsonify
import json
import requests
from bs4 import BeautifulSoup
from openai import AzureOpenAI
from flasgger import Swagger, swag_from
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS

# Initialize Azure OpenAI
llm = AzureOpenAI(
    azure_endpoint="https://genral-openai.openai.azure.com/",
    api_key="8929107a6a6b4f37b293a0fa0584ffc3",
    api_version="2024-02-01"
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Swagger UI setup
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "AutoML APIs"}
)
app.register_blueprint(swaggerui_blueprint)

swagger = Swagger(app, template={
    "info": {
        "title": "AutoML APIs",
        "description": "API for Automated Machine Learning tool",
        "version": "1.0.0"
    },
    "host": "https://reportdetailsapi-ecepdycjh4ekhsbr.eastus-01.azurewebsites.net",
    "basePath": "/",
})


def fetch_url_content(url):
    """
    Fetch the main content from a URL.
    """
    try:
        print(f"Fetching content from {url}...")
        response = requests.get(url, timeout=10)  # Add a timeout for better control
        response.raise_for_status()  # Check for HTTP errors
        print(f"Fetched content from {url}")
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except requests.exceptions.Timeout:
        print(f"Timeout occurred while fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request exception occurred: {e}")
        return None
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None



def fetch_urls(موضوع_التقرير, منظور_التقرير):
    """
    Fetch URLs based on موضوع التقرير and منظور التقرير using an external API.
    """
    try:
        api_endpoint = "https://ndc-bing-search-hrhra6fkcuaffjby.canadacentral-01.azurewebsites.net/bing_search"
        print(منظور_التقرير)
        print(موضوع_التقرير)
        payload = {
            "منظور_التقرير": منظور_التقرير,
            "موضوع_التقرير": موضوع_التقرير
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(api_endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("URLs", [])
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def process_with_llm(content, query):
    try:
        conversation_history = [
            {"role": "system", "content": "You are an Arabic journalist tasked with enriching content for a report."},
            {"role": "user", "content": f"Here is the content from the webpage:\n\n{content}\n\n{query}"}
        ]
        response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content
        return response
    except Exception as e:
        print(f"Error processing content with LLM: {e}")
        return None
def process_with_llm(content, query):
    try:
        conversation_history = [
            {"role": "system", "content": "You are an Arabic journalist tasked with enriching content for a report."},
            {"role": "user", "content": f"Here is the content from the webpage:\n\n{content}\n\n{query}"}
        ]
        response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content
        return response
    except Exception as e:
        print(f"Error processing content with LLM: {e}")
        return None

@app.route('/edit-arabic-report', methods=['POST'])
def edit_arabic_report():
    """
    API endpoint to edit an Arabic report JSON using GPT-4o with additional URL content enrichment.
    """
    try:
        data = request.get_json()
        json_input_string = data.get('json_input')
        arabic_prompt = data.get('arabic_prompt')

        if not json_input_string or not arabic_prompt:
            return jsonify({"error": "Both 'json_input' and 'arabic_prompt' are required."}), 400

        try:
            input_json = json.loads(json_input_string)
            print("Input JSON:", input_json)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

        # Ensure 'headings' exists
        headings = input_json.get("headings", [])
        if not isinstance(headings, list):
            return jsonify({"error": "'headings' must be a list."}), 400
        prompt = f"""
   المقال الحالي يتحدث عن:
{json.dumps(headings, ensure_ascii=False, indent=2)}

استخرج موضوع المقال في جملة واحدة بناءً على النص، ثم حدد منظور التقرير بحيث يحتوي على اثنان أو ثلاثة من الخيارات التالية كحد أقصى: [سياسي, إقتصادي, إجتماعي, تكنولوجي, بيئي, ثقافي, علمي, قانوني].

يجب أن تكون الإجابة بهذه الصيغة فقط (دون أي إضافات):

موضوع التقرير= <العنوان>
منظور التقرير= [<القيم الثلاث فقط>]
تأكد من عدم حذف أي جزء من الإجابة المطلوبة، ولا تضف أي شرح أو تفاصيل إضافية. لاحظ مكان الهمزة في الكلمات مثل: إقتصادي.


    """
        conversation_history = [
            {"role": "system", "content": "أنت مساعد متخصص في تحليل النصوص."},
            {"role": "user", "content": prompt}
        ]
        llm_response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content

        if "موضوع التقرير=" in llm_response and "منظور التقرير=" in llm_response:
            try:
                topic = llm_response.split("موضوع التقرير=")[1].split("\n")[0].strip()
                perspective = llm_response.split("منظور التقرير=")[1].strip().strip("[]").split(",")
                perspective = [p.strip() for p in perspective]
            except IndexError as e:
                return jsonify({"error": f"Error parsing LLM response: {str(e)}"}), 500
        else:
            return jsonify({"error": "LLM response is missing required fields ('موضوع التقرير=' or 'منظور التقرير=')."}), 500


        # Fetch URLs and content
        urls = fetch_urls(topic, perspective)
        url_contents = [fetch_url_content(url) for url in urls if fetch_url_content(url)]

        # Enrich prompt with URL contents
        enriched_prompt = arabic_prompt + "\n\n" + "يرجى تضمين إحصائيات وتحليلات مفصلة في كل نقطة، وشرح وافٍ و مفصل و كثيف بالمحتوى مع تقسيم المقال إلى أكثر من عنوان فرعي. استخدم البيانات التالية من المصادر لدعم المحتوى:\n\n".join(url_contents)
        conversation_history.append({
    "role": "system",
    "content": "You are a professional journalist tasked with writing a detailed informative and valuable Arabic article in JSON format. The output should contain detailed statistics and analysis for every point."
})

        conversation_history.append({
    "role": "user",
    "content": f"""
    قي نفس شكل ال JSON Formatبدون اي تغيير فيه, انا اريد الJson فقط بدون اي شروحات اضافية او في ال style قم بتحسين المقال التالي:\n{enriched_prompt}
    يجب ان كل  content يحتوي من عشر لخمسة عشر فقرات كبار و طوال مليئين بالتفاصيل الغنية 

يجب ان كل  content يحتوي على من خمس لسبع فقرات كبار و طوال مليئين بالتفاصيل الغنية 
برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بقول "حسب ذلك المصدر" ثم تقدم البرهان المناسب.
لا تنسى ال tables اذا احتاج الامر في ال content
أنا اريد فقط في الاجابة ال JSON file بدون اي شروحات اضافية
قم بإرجاع JSON صالح فقط بدون أي نصوص إضافية أو شروحات. يجب أن يبدأ الرد بـ "{" وينتهي بـ "}".
لا تقم بتغيير ال Format لل {input_json}
لا تقوم بنقص اي من ال{input_json} بل قم بالتزويد عليها
لا حظ انك لا تقوم بكتابة heading جديد ولكن انت تضيف نقطة جديدة ب title & content و كل ذلك مضاف على ال input
انت لا تقوم بتغيير اي شي الا ال content لاي من النقاط المتعارف عليها من ال input او انك تقوم بزيادة النقاط بcontent جديد دون الغاء القديم المتعارف عليه سابقا
يجب ان تكون الاجابة في شكل JSON فقط يتكون من :    
    **تفاصيل المحتوى المطلوب:**
    - يجب أن يحتوي كل "content" على 5-7 فقرات مفصلة وغنية بالتفاصيل.
    - انا لا اريد كتابة كلمة او مصطلح وسط المحتوى في ال content بين "" لكن اريد بين ()
    - استخدم علامات HTML صحيحة ودقيقة (<p></p>، <table></table>، إلخ.).
    - إذا كان هناك حاجة لعرض جداول، قم بتضمينها مع ذكر مصدرها أسفل الجدول.
    - قدم المحتوى مدعومًا بالإحصائيات والمصادر الموثوقة (على سبيل المثال، "حسب ذلك المصدر").
    - لا تستخدم علامات الاقتباس ("") داخل محتوى الفقرات، واستخدم الأقواس العادية () عند الحاجة.
    - تأكد من تصحيح الأخطاء الإملائية وأي مشاكل في التنسيق (مثل </p>>).
    - لا تنسى ال tables اذا احتاج الامر في ال content
    - انت لا تقوم بتغيير اي شي الا ال content لاي من النقاط المتعارف عليها من ال input او انك تقوم بزيادة النقاط بcontent جديد دون الغاء القديم المتعارف عليه سابقا
    
    **الإجابة المطلوبة:**
    - أريد ملف JSON صالحًا فقط يبدأ بـ "{" وينتهي بـ "}".
    - يجب أن تكون الإجابة بصيغة JSON صحيحة تمامًا، تبدأ بـ "{" وتنتهي بـ "}" دون أي نصوص إضافية خارج تنسيق JSON.

    - لا أريد أي شروحات أو نصوص إضافية في الإجابة.
    - قم بإرجاع المحتوى وفق الصيغة المطلوبة فقط.

    تأكد أن ملف JSON الناتج:
    - يحتوي على الحقول "headings" و"listItemsList" و"listItems" فقط مكتملة وصحيحة دون التزويد عليهم او الانقاص من احدهم.
    - متناسق وصالح للاستخدام بدون أي أخطاء في التنسيق.
    - يبدأ وينتهي بـ "{" و"}".

    لا حظ انك لا تقوم بكتابة heading جديد ولكن انت تضيف نقطة جديدة ب title & content و كل ذلك مضاف على ال input

    ال headings  يجب ان تكون array of objects
    تاكد من كتابة ال HTML Tags بشكل صحيح
تاكد اني اريد فقط ال JSON File بدون اي اضافات او شروحات
تاكد اني اريد JSON صحيح بدون errors: 
قم بتصحيح العلامة </p>> غير المتطابقة إلى </p> 
إزالة المسافات الزائدة وإصلاح الأخطاء الإملائية في جميع الأقسام.
تأكد من تنسيق كافة العلامات بشكل صحيح.
أكمل محتوى لاي من النقاط أو قم بإزالة الجزء الناقص.
انت لا تقوم بتغيير اي شي الا ال content لاي من النقاط المتعارف عليها من ال input او انك تقوم بزيادة النقاط بcontent جديد دون الغاء القديم المتعارف عليه سابقا
فانت لا تقوم باكتابة heading جديد بل نقطة جديدة
    لا تنسى ال tables اذا احتاج الامر في ال content
     صيغة المدخل:
سيتم إدخال JSON يحتوي على نصوص عربية (HTML)، كما في المثال التالي:

  "headings": تحتوي على
      "version": 1,
      "title": "عنوان رئيسي للنقاط", 
      "listItemsList": 
         تحتوي على
         "listItems": 
             تحتوي على
             "title": "عنوان فرعي لنقطة فرعية"
            "content": "<p>محتوى تلك النقطة</p>",
              
            
          
        
صيغة الإخراج المتوقعة:
ملف JSON صالح ومصحح يتبع نفس البنية، مع كتابة و تعديل المحتوى.
    """
})

        enriched_response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content
        print("Raw API response:", enriched_response)


        # Parse the enriched GPT response
        cleaned_response = enriched_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[len('```json'):].strip()
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3].strip()
        cleaned_response = cleaned_response.replace('`', '').strip()
            
        print("cleaned1: ", cleaned_response)
        return cleaned_response, 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

        

@app.route("/")
def hello_world():
    return "<p>Arabic Report Editor is running!</p>"

if __name__ == '__main__':
    app.run(debug=True)
