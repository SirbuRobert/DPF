import torch
import spacy
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline, T5ForConditionalGeneration
from langdetect import detect, LangDetectException
import os
from typing import List, Union, Dict

# --- CONFIGURATION (PATHS & HYPERPARAMETERS) ---

# Calculează directorul absolut al fișierului ai_pipeline.py
AI_MODULE_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Căi de model calculate (ESENȚIAL pentru rezolvarea erorii Repo ID)
QUIZ_MODEL_PATH = os.path.join(AI_MODULE_BASE_DIR, "quiz_model")          
SUMM_MODEL_PATH = os.path.join(AI_MODULE_BASE_DIR, "t5-large")
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-mul-en"
TRANSLATION_BACK_MODEL_NAME = "Helsinki-NLP/opus-mt-en-mul" 

# Hyperparametri T5
MAX_SRC_LEN_SUMM = 1024
MAX_SRC_LEN_QUIZ = 384
MAX_TARGET_LEN_QUIZ = 96

# Setare Dispozitiv
device = torch.device(
    "mps" if torch.backends.mps.is_available()
    else "cuda" if torch.cuda.is_available()
    else "cpu"
)

# ==============================================================================
# 1. INITIALIZARE TOATE MODELELE & VARIABILE GLOBALE
# ==============================================================================

models = {}
ORIGINAL_LANG = 'en' # Variabila globală
nlp = None
translator = None
translator_back = None
tok_quiz, model_quiz = None, None
tok_summ, model_summ = None, None


def load_model_components():
    global nlp, translator, translator_back, tok_quiz, model_quiz, tok_summ, model_summ
    
    # --- Încărcare Modele de Rezumare ---
    try:
        MODEL_NAME = "google-t5/t5-large"  # or your fine-tuned checkpoint path

        tok_summ = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            use_fast=True,
            model_max_length=1024,  # = MAX_INPUT_LEN from your config
            padding_side="right",
            truncation_side="right",
        )
        model_summ = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)

        #tok_summ = AutoTokenizer.from_pretrained(SUMM_MODEL_PATH)
        #model_summ = AutoModelForSeq2SeqLM.from_pretrained(SUMM_MODEL_PATH).to(device)
        model_summ.eval()
        models['summarize'] = True
    except Exception as e:
        print(f"EROARE: Nu s-a putut încărca modelul de rezumare ({SUMM_MODEL_PATH}): {e}")
        models['summarize'] = False
        return

    # --- Încărcare Modele de Generare Quiz ---
    try:
        tok_quiz = AutoTokenizer.from_pretrained(QUIZ_MODEL_PATH)
        model_quiz = T5ForConditionalGeneration.from_pretrained(QUIZ_MODEL_PATH).to(device)
        model_quiz.eval()
        nlp = spacy.load("en_core_web_sm")
        models['quiz'] = True
    except Exception as e:
        print(f"EROARE: Nu s-a putut încărca modelul de quiz/spaCy ({QUIZ_MODEL_PATH}): {e}")
        models['quiz'] = False
        return
        
    # --- Încărcare Modele de Traducere ---
    try:
        trans_tok = AutoTokenizer.from_pretrained(TRANSLATION_MODEL_NAME)
        trans_model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL_NAME).to(device)
        global translator
        translator = pipeline("translation", model=trans_model, tokenizer=trans_tok, device=0 if device.type != 'cpu' else -1)
        
        back_trans_tok = AutoTokenizer.from_pretrained(TRANSLATION_BACK_MODEL_NAME)
        back_trans_model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_BACK_MODEL_NAME).to(device)
        global translator_back
        translator_back = pipeline("translation", model=back_trans_model, tokenizer=back_trans_tok, device=0 if device.type != 'cpu' else -1)
        
        models['translate'] = True
        models['translate_back'] = True
        print(f"🎉 Toate modelele necesare au fost încărcate cu succes.")
    except Exception as e:
        print(f"Atenție: Eroare la încărcarea modelelor de traducere. Traducerea este dezactivată: {e}")
        models['translate'] = False
        models['translate_back'] = False
        translator = None 

# Apelare funcție de încărcare
load_model_components()


# ==============================================================================
# 2. FUNCȚII DE PROCESARE (Traducere, Rezumare, Extracție, Quiz)
# ==============================================================================

def read_text_from_file(file_path):
    """Citeste intregul text dintr-un fisier."""
    if not os.path.exists(file_path): raise FileNotFoundError(f"Fișierul nu a fost găsit la calea specificată: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f: return f.read()

def keep_complete_sentences(text: str) -> str:
    """Păstrează doar propozițiile complete la sfârșitul unui string."""
    t = text.rstrip()
    idx = max(t.rfind("."), t.rfind("!"), t.rfind("?"))
    if idx == -1: return t
    i = idx + 1
    while i < len(t) and t[i] in '"\'”’)]}': i += 1
    return t[:i]


def translate_back_to_original(text_list: List[str]) -> List[str]:
    """
    Traduci o listă de stringuri din Engleză înapoi în limba originală (ORIGINAL_LANG).
    """
    if not models.get('translate_back') or ORIGINAL_LANG == 'en': return text_list
    target_prefix = f">>{ORIGINAL_LANG}<<"
    prefixed_texts = [target_prefix + " " + t for t in text_list]
    try:
        print(f"Traducere înapoi în [{ORIGINAL_LANG}]...")
        results = translator_back(prefixed_texts, max_length=1024, truncation=True)
        translated_texts = [res['translation_text'] for res in results]
        return translated_texts
    except Exception as e:
        print(f"Eroare la traducerea înapoi. Se returnează textul în Engleză: {e}")
        return text_list


def detect_and_translate(text: str) -> str:
    """Detectează limba și traduce textul în Engleză dacă nu este deja 'en'."""
    global ORIGINAL_LANG
    if not models['translate'] or not text.strip(): ORIGINAL_LANG = 'en'; return text
    try:
        detected_lang = detect(text)
        ORIGINAL_LANG = detected_lang
    except LangDetectException:
        detected_lang = "unknown"; ORIGINAL_LANG = 'en'
    if detected_lang == 'en': return text

    if translator:
        print(f"Traducere din {detected_lang} în Engleză...")
        try:
            result = translator(text, max_length=1024, truncation=True)
            print ("Traducere finalizată (EN):" , result[0]['translation_text'][:50] + "..." )
            return result[0]['translation_text']
        except Exception as e:
            print(f"Eroare la traducere. Se folosește textul original: {e}")
            return text
    return text


def summarize(texts: Union[str, List[str]], max_new_tokens: int = 150, num_beams: int = 4) -> List[str]:
    """Efectuează rezumarea pe textul procesat (deja tradus)."""
    if isinstance(texts, str): texts = [texts]; summaries = []
    for original_text in texts:
        # Aici se folosește textul deja tradus/procesat (din apelul run_full_pipeline)
        processed_text = original_text 
        
        enc = tok_summ([processed_text], return_tensors="pt", padding=True, truncation=True, max_length=MAX_SRC_LEN_SUMM).to(device)
        with torch.no_grad():
            out = model_summ.generate(
                **enc, max_new_tokens=max_new_tokens, num_beams=num_beams, length_penalty=0.3,
            )
        summary_raw = tok_summ.decode(out[0], skip_special_tokens=True)
        summaries.append(keep_complete_sentences(summary_raw)) 
    return summaries

def get_answer_type(answer: str) -> str:
    doc = nlp(answer)
    if doc.ents: return doc.ents[0].label_
    return "CONCEPT" 

def extract_answers_using_ner(context: str) -> list[str]:
    doc = nlp(context); potential_answers = []; seen_answers = set()
    primary_ner_labels = ['PERSON', 'ORG', 'DATE', 'GPE', 'LOC', 'CARDINAL', 'EVENT', 'TIME', 'PRODUCT', 'NORP', 'LANGUAGE']
    for ent in doc.ents:
        answer_text = ent.text.strip()
        if ent.label_ in primary_ner_labels and len(answer_text) > 3 and answer_text not in seen_answers:
            potential_answers.append(answer_text); seen_answers.add(answer_text)
    for chunk in doc.noun_chunks:
        answer_text = chunk.text.strip()
        if len(answer_text.split()) > 1 and len(answer_text) > 6 and answer_text not in seen_answers and not answer_text.lower().startswith(('the ', 'a ', 'an ')):
            potential_answers.append(answer_text); seen_answers.add(answer_text)
    return potential_answers

def generate_question(context: str, answer: str) -> str:
    input_text = f"answer: {answer} context: {context}"
    input_ids = tok_quiz(input_text, max_length=MAX_SRC_LEN_QUIZ, truncation=True, return_tensors="pt").input_ids.to(device)
    with torch.no_grad():
        outputs = model_quiz.generate(input_ids=input_ids, max_length=MAX_TARGET_LEN_QUIZ, num_beams=4, early_stopping=True)
    return tok_quiz.decode(outputs[0], skip_special_tokens=True)

def is_semantically_valid(question: str, answer_type: str) -> bool:
    question_lower = question.lower()
    semantic_map = {
        'PERSON': ('who', 'whom', 'whose'), 'LOC': ('where', 'what'), 'DATE': ('when', 'in what year'), 
        'CARDINAL': ('how many', 'what number'), 'CONCEPT': ('what', 'which', 'define', 'explain', 'what is'), 
        'ORG': ('what', 'which', 'who', 'name'), 'GPE': ('where', 'what', 'which'),
        'UNKNOWN': ('what', 'which'), 
    }
    expected_starts = semantic_map.get(answer_type, ('what', 'which')); 
    return any(question_lower.startswith(start) for start in expected_starts)

def generate_quiz_from_context(large_context: str, max_questions: int) -> list[Dict]:
    doc = nlp(large_context)
    quiz_results = []
    
    for sent in doc.sents:
        if len(quiz_results) >= max_questions: break
        sentence_text = sent.text.strip()
        if len(sentence_text.split()) < 5: continue

        answers_in_sentence = extract_answers_using_ner(sentence_text)
        
        for answer in answers_in_sentence:
            if len(quiz_results) >= max_questions: break
                
            answer_type = get_answer_type(answer)
            question = generate_question(sentence_text, answer)
            
            if is_semantically_valid(question, answer_type):
                quiz_results.append({
                    "source_sentence": sentence_text, "answer": answer, "answer_type": answer_type, "question": question
                })
            
    return quiz_results


# ==============================================================================
# 3. FUNCȚIA PRINCIPALĂ DE EXECUȚIE A PIPELINE-ULUI (MODIFICATĂ PENTRU RETURN)
# ==============================================================================

def run_full_pipeline(input_file_path: str, num_questions: int, max_tokens_summ: int = 150, num_beams_summ: int = 4) -> Dict:
    """
    Execută fluxul complet și returnează dicționarul de rezultate.
    """
    try:
        original_text = read_text_from_file(input_file_path)
    except FileNotFoundError:
        print(f"\nEROARE: Fișierul de intrare nu a fost găsit la calea: {input_file_path}")
        return None

    # --- PASUL 1: DETECTARE ȘI TRADUCERE ÎNAINTE ---
    translated_text_for_processing = detect_and_translate(original_text)
    
    # 2. Rezumare
    summarized_results_en = summarize(translated_text_for_processing, max_tokens_summ, num_beams_summ)
    final_summary_en = summarized_results_en[0]
    
    # 3. Generare Quiz
    quiz_list_en = generate_quiz_from_context(final_summary_en, max_questions=num_questions)

    # --- PASUL 4: TRADUCERE ÎNAPOI (POST-PROCESARE) ---
    
    final_results = quiz_list_en
    final_summary_ro = final_summary_en

    if ORIGINAL_LANG != 'en' and models.get('translate_back'):
        # Logica de traducere înapoi (folosind datele EN)
        strings_to_translate = [final_summary_en]
        for item in quiz_list_en:
            strings_to_translate.append(item['question'])
            strings_to_translate.append(item['answer'])
            
        translated_back_list = translate_back_to_original(strings_to_translate)
        
        final_summary_ro = translated_back_list[0]
        quiz_list_ro = []
        
        for i in range(len(quiz_list_en)):
            q_index = 1 + 2 * i 
            a_index = 2 + 2 * i
            
            quiz_list_ro.append({
                "question": translated_back_list[q_index],
                "answer": translated_back_list[a_index],
                "source_sentence": quiz_list_en[i]['source_sentence'] 
            })
            
        final_results = quiz_list_ro
        
    else:
        # Nu a fost nevoie de traducere
        pass

    # 7. Returnează un dicționar cu toate datele necesare (Vizibil în views.py)
    return {
        'quiz_results': final_results,
        'final_summary': final_summary_ro,
        'original_lang': ORIGINAL_LANG
    }


if __name__ == '__main__':
    # ... (Blocul de execuție) ...
    FILE_PATH_INPUT = "input.txt"
    FILE_PATH_OUTPUT = 'output.txt'
    QUESTION_COUNT = 7      
    MAX_TOKENS_SUMMARY = 150

    with open(FILE_PATH_INPUT, encoding='utf-8') as input_file:
        test_text_ro = input_file.read()
    
    try:
        with open(FILE_PATH_OUTPUT, 'w', encoding='utf-8') as f:
            f.write(test_text_ro)
        
        # Apelarea funcției principale cu toți parametrii
        result = run_full_pipeline(FILE_PATH_OUTPUT, QUESTION_COUNT, MAX_TOKENS_SUMMARY)
        
        # Afișarea în consolă a rezultatului returnat (pentru debug)
        print("\n--- REZULTAT RETURNAT CĂTRE DJANGO ---")
        print(f"Rezumat: {result['final_summary']}")
        print(f"Întrebări: {len(result['quiz_results'])}")
        print(f"Întrebări: {result['quiz_results']}")
        for i, qa in enumerate(result['quiz_results'], 1):
            print(f"Q{i}: {qa['question']} | A: {qa['answer']}")

    except Exception as e:
        print(f"\nO eroare majoră a intervenit în execuția pipeline-ului: {e}")