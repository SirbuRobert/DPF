import torch
import spacy
from transformers import T5ForConditionalGeneration, AutoTokenizer
import os # Necesită import pentru citirea fișierelor

# --- CONFIGURATION ---
FINAL_PATH = "./quiz_model" 
MAX_INPUT_LENGTH = 384
MAX_TARGET_LENGTH = 96

# ==============================================================================
# 1. LOAD MODELS AND SETUP DEVICE
# ==============================================================================
# A. Load T5 Question Generation Model
try:
    qg_model = T5ForConditionalGeneration.from_pretrained(FINAL_PATH)
    qg_tokenizer = AutoTokenizer.from_pretrained(FINAL_PATH)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    qg_model.to(device)
    qg_model.eval()
    nlp = spacy.load("en_core_web_sm")
    print("🎉 Modelele T5 și spaCy au fost încărcate cu succes.")
except Exception as e:
    print(f"Eroare la încărcarea modelelor. Verificați calea ({FINAL_PATH}) și instalările spaCy/PyTorch: {e}")
    exit()

# ==============================================================================
# 2. HELPER FUNCTIONS: GENERATION & EXTRACTION (Rămân aceleași)
# ==============================================================================

def get_answer_type(answer: str) -> str:
    """Uses spaCy to determine the primary NER label or defaults to CONCEPT."""
    doc = nlp(answer)
    if doc.ents:
        return doc.ents[0].label_
    return "CONCEPT" 

def extract_answers_using_ner(context: str) -> list[str]:
    """Identifies both Named Entities and Noun Phrases (Concepts)."""
    doc = nlp(context)
    potential_answers = []
    seen_answers = set()
    
    # 1. Extract Named Entities 
    primary_ner_labels = ['PERSON', 'ORG', 'DATE', 'GPE', 'LOC', 'CARDINAL', 'EVENT', 'TIME', 'PRODUCT', 'NORP', 'LANGUAGE']
    for ent in doc.ents:
        answer_text = ent.text.strip()
        if ent.label_ in primary_ner_labels and len(answer_text) > 3 and answer_text not in seen_answers:
            potential_answers.append(answer_text)
            seen_answers.add(answer_text)

    # 2. Extract Noun Chunks (Concepts)
    for chunk in doc.noun_chunks:
        answer_text = chunk.text.strip()
        if len(answer_text.split()) > 1 and len(answer_text) > 6 and answer_text not in seen_answers and not answer_text.lower().startswith(('the ', 'a ', 'an ')):
            potential_answers.append(answer_text)
            seen_answers.add(answer_text)
            
    return potential_answers

def generate_question(context: str, answer: str) -> str:
    """Generates a question from a given context (sentence) and answer."""
    input_text = f"answer: {answer} context: {context}"
    input_ids = qg_tokenizer(
        input_text, max_length=MAX_INPUT_LENGTH, truncation=True, return_tensors="pt"
    ).input_ids.to(device)

    with torch.no_grad():
        outputs = qg_model.generate(
            input_ids=input_ids, max_length=MAX_TARGET_LENGTH, num_beams=4, early_stopping=True 
        )
    return qg_tokenizer.decode(outputs[0], skip_special_tokens=True)

def is_semantically_valid(question: str, answer_type: str) -> bool:
    """Checks if the question's starting word aligns with the answer's type."""
    question_lower = question.lower()
    semantic_map = {
        'PERSON': ('who', 'whom', 'whose'), 'LOC': ('where', 'what'), 'DATE': ('when', 'in what year'), 
        'CARDINAL': ('how many', 'what number'), 'CONCEPT': ('what', 'which', 'define', 'explain', 'what is'), 
        'ORG': ('what', 'which', 'who', 'name'), 'GPE': ('where', 'what', 'which'),
        'UNKNOWN': ('what', 'which'), 
    }
    
    expected_starts = semantic_map.get(answer_type, ('what', 'which')) 
    
    for start in expected_starts:
        if question_lower.startswith(start):
            return True
            
    return False

# ==============================================================================
# 3. CORE LOGIC: GENERATE QUIZ FUNCTION
# ==============================================================================

def generate_quiz_from_context(large_context: str, max_questions: int) -> list[dict]:
    """
    Main function: Segments the large text, extracts answers, validates them, 
    and generates questions up to the specified limit.
    """
    doc = nlp(large_context)
    quiz_results = []
    
    for sent in doc.sents:
        if len(quiz_results) >= max_questions:
            break
            
        sentence_text = sent.text.strip()
        if len(sentence_text.split()) < 5:
            continue

        answers_in_sentence = extract_answers_using_ner(sentence_text)
        
        for answer in answers_in_sentence:
            if len(quiz_results) >= max_questions:
                break
                
            answer_type = get_answer_type(answer)
            question = generate_question(sentence_text, answer)
            
            if is_semantically_valid(question, answer_type):
                quiz_results.append({
                    "source_sentence": sentence_text,
                    "answer": answer,
                    "answer_type": answer_type,
                    "question": question
                })
            
    return quiz_results

# ==============================================================================
# 4. EXECUTION MODE (Input File and Variables)
# ==============================================================================

def read_text_from_file(file_path):
    """Citeste intregul text dintr-un fisier."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fișierul nu a fost găsit la calea specificată: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def generate_full_quiz(input_file_path: str, num_questions: int):
    """
    Functia principala care coordoneaza citirea si generarea quiz-ului.
    """
    try:
        # Citeste textul din fisier
        input_text = read_text_from_file(input_file_path)
    except FileNotFoundError as e:
        print(f"EROARE: {e}")
        return

    print("\n" + "="*70)
    print(f"GENERARE QUIZ: {input_file_path} (Max {num_questions} întrebări)")
    print("="*70)
    print(f"Text sursă (început): {input_text[:100]}...\n")

    # Genereaza quiz-ul
    quiz_list = generate_quiz_from_context(input_text, max_questions=num_questions)

    print("\n--- Rezultate Quiz ---")
    if not quiz_list:
        print("Nu au fost generate întrebări valide după filtrare.")
    else:
        for i, item in enumerate(quiz_list):
            print(f"{i+1}. Question: **{item['question']}**")
            print(f"   (Correct Answer: {item['answer']}) (Type: {item['answer_type']})")
            print(f"   [Source Sentence: {item['source_sentence'][:70]}...]")
            print("-" * 20)


if __name__ == '__main__':
    # ⚠️ EXEMPLU DE UTILIZARE: 
    # 1. Asigurati-va ca aveti un fisier numit 'input.txt' in directorul curent.
    # 2. Definiti numarul de intrebari dorit.

    # --- PARAMETRII DE INTRARE ---
    FILE_PATH = "input.txt"  # <--- SCHIMBATI ACEASTA CALE LA FISIERUL DVS.
    QUESTION_COUNT = 7       # <--- NUMARUL DE INTREBARI DORIT
    # -----------------------------
    
    # ⚠️ DEBUG: Creeaza un fisier temporar pentru a face demo-ul sa functioneze
    # INLOCUITI CU TEXTUL DVS. REAL!
    temp_text = (
        "The Sumerians are a collection of city-states in southern Mesopotamia, including Ur, Bad-tibira, and Eridu, which is believed to be the oldest city in the region. In about 5000 BCE, nomads living in the region began to settle in the fertile land near the Tigris and Euphrates Rivers. They formed small villages which eventually developed into the civilization known as Sumer."
    )
    try:
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(temp_text)
        
        generate_full_quiz(FILE_PATH, QUESTION_COUNT)
        
        # Sterge fisierul temporar
        # os.remove(FILE_PATH)
        
    except Exception as e:
        print(f"O eroare a intervenit în timpul execuției: {e}")