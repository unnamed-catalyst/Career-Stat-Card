"""
Fixture personas for eval.py. All people and companies are fictional.

Each fixture states the Overall range the author expects. These are
hand-set sanity bands, not ground-truth labels: they catch scoring that is
clearly wrong (a new graduate rated gold, a mismatched candidate rated highly).
"""

FIXTURES = [
    {
        "id": "senior_ml_engineer",
        "description": "Senior ML engineer, 8 years",
        "job_description": "Senior Machine Learning Engineer at a cloud-native AI startup",
        "expected_overall": (72, 92),
        "resume": """Jane Smith
Senior Machine Learning Engineer, 8 years of experience
Experience:
- Led ML platform team at Acme Corp (2019-present): built real-time inference pipeline serving 50M predictions/day on AWS SageMaker; reduced p99 latency from 420ms to 85ms via model quantisation and batching.
- ML Engineer at DataCo (2016-2019): shipped NLP classification models for customer support routing (92% accuracy); owned model retraining pipeline in Airflow.
Skills: Python, PyTorch, TensorFlow, FastAPI, AWS (SageMaker, Lambda, S3), Docker, Kubernetes, SQL, Spark, MLflow, Airflow.
Education: M.Sc. Computer Science (Machine Learning), Stanford University, 2016.""",
    },
    {
        "id": "fresh_graduate",
        "description": "New CS graduate, no industry experience",
        "job_description": "Junior Software Engineer",
        "expected_overall": (45, 70),
        "resume": """Alex Johnson
Computer Science Graduate, 0 years of industry experience
Education: B.Sc. Computer Science, University of Toronto, 2024. GPA 3.7.
Projects:
- Built a sentiment analysis classifier using BERT fine-tuning (PyTorch) as a course project; achieved 89% accuracy on SST-2.
- Developed a REST API in Flask for a to-do app; deployed on Heroku.
Skills: Python, Java, PyTorch, Flask, Git, SQL (basic).""",
    },
    {
        "id": "career_changer",
        "description": "Quant analyst moving into ML, 6 years",
        "job_description": "Machine Learning Engineer at an automotive AI company",
        "expected_overall": (55, 82),
        "resume": """Michael Lee
Quantitative Analyst, 6 years in finance, transitioning to ML engineering
Experience:
- Quant Analyst at Hedge Fund XYZ (2018-present): built statistical models in Python (pandas, numpy, scikit-learn) for equity signal generation; automated reporting pipelines that saved 12 hrs/week.
- Analyst at Investment Bank ABC (2016-2018): financial modelling in Excel and Python; presented findings to senior stakeholders.
Recent upskilling: Completed fast.ai deep learning course; built an image classifier deployed on a Flask API; studying MLOps on Coursera.
Skills: Python, scikit-learn, pandas, numpy, SQL, Git, basic PyTorch.
Education: B.Sc. Mathematics & Statistics, McGill University, 2016.""",
    },
    {
        "id": "senior_backend",
        "description": "Staff backend engineer, 12 years",
        "job_description": "Senior Backend Engineer, payments platform",
        "expected_overall": (75, 95),
        "resume": """Priya Raman
Staff Software Engineer, 12 years of experience
Experience:
- Staff Engineer at PayGrid (2019-present): designed the ledger service processing $4B/year with exactly-once semantics on Kafka and PostgreSQL; led a team of 6.
- Senior Engineer at ShopStack (2015-2019): split a Rails monolith into 14 Go services; cut checkout latency by 60%.
- Software Engineer at Telco One (2012-2015): built billing integrations in Java.
Skills: Go, Java, Python, PostgreSQL, Kafka, Kubernetes, AWS, gRPC, system design.
Education: B.Eng. Computer Engineering, University of Waterloo, 2012.""",
    },
    {
        "id": "data_analyst",
        "description": "Data analyst, 2 years",
        "job_description": "Data Analyst at a retail company",
        "expected_overall": (55, 80),
        "resume": """Sam Ortiz
Data Analyst, 2 years of experience
Experience:
- Data Analyst at FreshMart (2023-present): built Tableau dashboards used by 40 store managers; wrote SQL models in dbt; ran A/B test analysis for promotions.
- Analytics Intern at CityBank (2022): cleaned customer data in Python and Excel.
Skills: SQL, Python (pandas), Tableau, dbt, Excel, statistics.
Education: B.A. Economics, UBC, 2022.""",
    },
    {
        "id": "role_mismatch",
        "description": "Graphic designer applying for a backend role",
        "job_description": "Backend Engineer (Python, distributed systems)",
        "expected_overall": (45, 64),
        "resume": """Chris Park
Graphic Designer, 5 years of experience
Experience:
- Senior Designer at Brightside Studio (2021-present): led brand identity projects for 20+ clients; managed print and digital campaigns.
- Designer at PixelWorks (2019-2021): created social media assets and packaging designs.
Skills: Adobe Illustrator, Photoshop, InDesign, Figma, typography, basic HTML/CSS.
Education: BFA Graphic Design, OCAD University, 2019.""",
    },
]

# (higher, lower): the first persona's Overall must beat the second's.
ORDERING = [
    ("senior_ml_engineer", "fresh_graduate"),
    ("senior_backend", "role_mismatch"),
    ("senior_ml_engineer", "role_mismatch"),
]
