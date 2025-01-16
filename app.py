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
            {"role": "system", "content": "You are an Arabic journalist tasked with enriching content for a report in a JSON File."},
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

استخرج موضوع المقال في جملة واحدة بناءً على النص، ثم حدد منظور التقرير بحيث يحتوي على واحد أو اثنان من الخيارات التالية كحد أقصى: [سياسي, إقتصادي, إجتماعي, تكنولوجي, بيئي, ثقافي, علمي, قانوني].

يجب أن تكون الإجابة بهذه الصيغة فقط (دون أي إضافات):

موضوع التقرير= <العنوان>
منظور التقرير= [<القيم الاثنان فقط>]
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

        if "موضوع التقرير=" not in llm_response or "منظور التقرير=" not in llm_response:
           
            prompt = f"""
                المقال الحالي يتحدث عن:
                {json.dumps(headings, ensure_ascii=False, indent=2)}

                استخرج موضوع المقال في جملة واحدة بناءً على النص  قدم الإجابة كالتالي:
                <العنوان>
                قدم الاجابة في جملة واحدة عنوان واخد فقط بدون شروحات او اضافات اخرى جملة واحدة فقط
                """
            conversation_history = [
                            {"role": "system", "content": "أنت مساعد متخصص في تحليل النصوص."},
                            {"role": "user", "content": prompt}
                        ]
            llm_response = llm.chat.completions.create(
                            model="gpt-4o",
                            messages=conversation_history
                        ).choices[0].message.content
            topic=llm_response
            perspective= ["غير_محدد"]

        else:

            topic = llm_response.split("موضوع التقرير=")[1].split("\n")[0].strip()
            perspective = llm_response.split("منظور التقرير=")[1].strip().strip("[]").split(",")
            perspective = [p.strip() for p in perspective]


        # Fetch URLs and content
        urls = fetch_urls(topic, perspective)
        url_contents = [fetch_url_content(url) for url in urls if fetch_url_content(url)]

        # Enrich prompt with URL contents
        enriched_prompt = arabic_prompt + "\n\n" + "يرجى تضمين إحصائيات وتحليلات مفصلة في كل نقطة، وشرح وافٍ و مفصل و كثيف بالمحتوى مع تقسيم المقال إلى أكثر من عنوان فرعي. استخدم البيانات التالية من المصادر لدعم المحتوى:\n\n".join(url_contents)
        conversation_history.append({
    "role": "system",
    "content": "You are a professional journalist tasked with editing and writing a detailed informative and valuable Arabic article in JSON format. You are a professional analyst and journalist with a keen ability to provide detailed informative, valuable,  predictive insights and detailed forecasting. Your task is to write a detailed Arabic article in JSON format, not as a string. The output should contain comprehensive statistics, predictive analysis, and future trends for each point under a specific heading. The input JSON will contain headings and key points, and your mission is to enhance each point with in-depth forecasts, valuable insights, and actionable recommendations under its respective heading.The output should contain detailed statistics and analysis for every point."
})

        conversation_history.append({
    "role": "user",
    "content": f"""
    قي نفس شكل ال JSON Formatبدون اي تغيير فيه, انا اريد الJson فقط بدون اي شروحات اضافية او في ال style قم بتحسين المقال التالي:\n{enriched_prompt}
    يجب ان كل  content يحتوي من عشر لخمسة عشر فقرات كبار و طوال مليئين بالتفاصيل الغنية 

يجب ان كل  content يحتوي على من خمس لسبع فقرات كبار و طوال مليئين بالتفاصيل الغنية 
برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بذكر اسم المصدر المستخدم فلا "حسب ذلك المصدر" فقط بل اذكر اسمه او عنوانه  و بيانات عنه مثل تاريخ نشره مثل اسم الكاتب و اسم الموقع او الصحيفة او الجريدة اذا توفر اسمه فيكون ذلك لحفظ حقوق المصدر ثم تقدم البرهان المناسب.
لا تنسى ال tables اذا احتاج الامر في ال content
أنا اريد فقط في الاجابة ال JSON file بدون اي شروحات اضافية
قم بإرجاع JSON صالح فقط بدون أي نصوص إضافية أو شروحات. يجب أن يبدأ الرد بـ "{" وينتهي بـ "}".
في ال content يجب ان تشير على توقعاتك بناء على المصادر و تسرد مجموعة توقعات قيمة و بناءة تلك التوقعات تكون بناء على المصادر و تاخذ في حسبانك جميع الجوانب السياسية و الاجتماعية و الدينية و الاقتصادية مع ذكر خطوات ستتطبعها تلك الجهة السياسية المصرية الصادر اليها التقرير 
لا تقم بتغيير ال Format لل {input_json}
لا تقوم بنقص اي من المعلومات و المحتوى من ال{input_json} بل قم بالتعديل و بالتزويد عليها
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
    - في ال content يجب ان تشير على توقعاتك بناء على المصادر و تسرد مجموعة توقعات قيمة و بناءة تلك التوقعات تكون بناء على المصادر و تاخذ في حسبانك جميع الجوانب السياسية و الاجتماعية و الدينية و الاقتصادية مع ذكر خطوات ستتطبعها تلك الجهة السياسية المصرية الصادر اليها التقرير 
    - في ال content اذكر الخطوات و القرارات التي ستتخذها تلك الجهة السيادية المستهدفة من التقرير في شكل نقاط
    - لا تنسى ان تزيد دائما توقعاتك و تنبؤاتك و رايك في ال content لكل نقطة مزودة بالارقام و التواريخ و الاحصائيات
    - توقعاتك يجب ان تكون فيها رأي مبرهن بالمصادر مع تواريخ و ارقام و احصائيات و قل انها المتوقعة 
    - دائما اذكر رأيك و لا تتكلم بشكل عام بل تكلم اكثر بشكل أخص
    - برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بذكر اسم المصدر المستخدم فلا "حسب ذلك المصدر" فقط بل اذكر اسمه او عنوانه  و بيانات عنه مثل تاريخ نشره مثل اسم الكاتب و اسم الموقع او الصحيفة اذا توفر اسمه فيكون ذلك لحفظ حقوق المصدر ثم تقدم البرهان المناسب.
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

  "headings": تحتوي على  only one array 
      "version": 1,
      "title": "عنوان رئيسي للنقاط", 
      "listItemsList": 
         تحتوي على
         "listItems": 
             تحتوي على
             "title": "عنوان فرعي لنقطة فرعية"
            "content": "<p>محتوى تلك النقطة</p>",
              
            
          
        
صيغة الإخراج المتوقعة:
لا تنسى ال tables اذا احتاج الامر على الاقل في نقطة واحدة في ال content
  "headings" تحتوي على array واحد 
ملف JSON صالح ومصحح يتبع نفس البنية، مع كتابة و تعديل المحتوى.
في ال content يجب ان تشير على توقعاتك بناء على المصادر و تسرد مجموعة توقعات قيمة و بناءة تلك التوقعات تكون بناء على المصادر و تاخذ في حسبانك جميع الجوانب السياسية و الاجتماعية و الدينية و الاقتصادية مع ذكر خطوات ستتطبعها تلك الجهة السياسية الصادر اليها التقرير 
في ال content اذكر الخطوات و القرارات التي ستتخذها تلك الجهة السيادية المستهدفة من التقرير في شكل نقاط
توقعاتك يجب ان تكون فيها رأي مبرهن بالمصادر مع تواريخ و ارقام و احصائيات و قل انها المتوقعة 
برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بذكر اسم المصدر المستخدم فلا "حسب ذلك المصدر" فقط بل اذكر اسمه او عنوانه  و بيانات عنه مثل تاريخ نشره مثل اسم الكاتب و اسم الموقع او الصحيفة اذا توفر اسمه فيكون ذلك لحفظ حقوق المصدر ثم تقدم البرهان المناسب.
لا تنسى ان تزيد دائما توقعاتك و تنبؤاتك و رايك في ال content لكل نقطة مزودة بالارقام و التواريخ و الاحصائيات
 دائما اذكر رأيك و لا تتكلم بشكل عام بل تكلم اكثر بشكل أخص
قم بارجاع الناتج النهائي في شكل JSON Format و احذر ان ترجع ب String Format

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
        edit_arabic_report()
        return jsonify({"error": str(e)}), 500

        

@app.route("/")
def hello_world():
    return "<p>Arabic Report Editor is running!</p>"

if __name__ == '__main__':
    app.run(debug=True)
