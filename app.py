"""Calculadora científica web con Streamlit.

Para ejecutar en Windows:
    py -m pip install -r requirements.txt
    py -m streamlit run app.py

Para publicar: sube app.py y requirements.txt a GitHub y conecta
el repositorio en https://share.streamlit.io/
"""

import ast
import html
import math
import operator
import re

import streamlit as st


# --------------------------- CÁLCULOS SEGUROS ---------------------------
OPERACIONES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

CONSTANTES = {"pi": math.pi, "e": math.e}


def numero_valido(valor):
    """Rechaza resultados infinitos, complejos o excesivamente grandes."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError("El resultado debe ser un número real.")
    try:
        como_float = float(valor)
    except (OverflowError, ValueError) as error:
        raise ValueError("El resultado es demasiado grande.") from error
    if not math.isfinite(como_float) or abs(como_float) > 1e100:
        raise ValueError("El resultado está fuera del rango permitido.")
    return valor


def aplicar_funcion(nombre, valor, modo_grados):
    numero_valido(valor)
    funciones = {
        "sqrt": math.sqrt,
        "ln": math.log,
        "log": math.log10,
        "exp": math.exp,
        "abs": abs,
    }
    if nombre in funciones:
        return funciones[nombre](valor)
    if nombre == "fact":
        if valor < 0 or valor != int(valor) or valor > 170:
            raise ValueError("El factorial requiere un entero de 0 a 170.")
        return math.factorial(int(valor))
    if nombre in ("sin", "cos", "tan"):
        angulo = math.radians(valor) if modo_grados else valor
        if nombre == "tan" and abs(math.cos(angulo)) < 1e-12:
            raise ValueError("La tangente no está definida en ese ángulo.")
        return getattr(math, nombre)(angulo)
    if nombre in ("asin", "acos", "atan"):
        respuesta = getattr(math, nombre)(valor)
        return math.degrees(respuesta) if modo_grados else respuesta
    raise ValueError("Función no permitida.")


def evaluar_nodo(nodo, modo_grados, ans):
    if isinstance(nodo, ast.Expression):
        return evaluar_nodo(nodo.body, modo_grados, ans)

    if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
        return numero_valido(nodo.value)

    if isinstance(nodo, ast.Name):
        if nodo.id == "ans":
            return numero_valido(ans)
        if nodo.id in CONSTANTES:
            return CONSTANTES[nodo.id]
        raise ValueError("Constante desconocida. Usa pi, e o ans.")

    if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.UAdd, ast.USub)):
        valor = evaluar_nodo(nodo.operand, modo_grados, ans)
        return numero_valido(-valor if isinstance(nodo.op, ast.USub) else valor)

    if isinstance(nodo, ast.BinOp) and type(nodo.op) in OPERACIONES:
        a = evaluar_nodo(nodo.left, modo_grados, ans)
        b = evaluar_nodo(nodo.right, modo_grados, ans)
        if isinstance(nodo.op, ast.Pow) and abs(b) > 100:
            raise ValueError("Exponente demasiado grande (máximo 100).")
        return numero_valido(OPERACIONES[type(nodo.op)](a, b))

    if (
        isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and len(nodo.args) == 1
        and not nodo.keywords
    ):
        argumento = evaluar_nodo(nodo.args[0], modo_grados, ans)
        return numero_valido(aplicar_funcion(nodo.func.id, argumento, modo_grados))

    raise ValueError("La expresión contiene una operación no permitida.")


def calcular_expresion(expresion, modo_grados=True, ans=0):
    if not isinstance(expresion, str) or not expresion.strip():
        raise ValueError("Escribe una operación para calcular.")
    if len(expresion) > 180:
        raise ValueError("La expresión es demasiado larga.")

    limpia = (
        expresion.replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("π", "pi")
        .replace("^", "**")
        .strip()
    )
    try:
        arbol = ast.parse(limpia, mode="eval")
        if sum(1 for _ in ast.walk(arbol)) > 100:
            raise ValueError("La expresión es demasiado compleja.")
        return numero_valido(evaluar_nodo(arbol, modo_grados, ans))
    except (SyntaxError, TypeError) as error:
        raise ValueError("Expresión incompleta o incorrecta.") from error
    except ZeroDivisionError as error:
        raise ValueError("No puedes dividir entre cero.") from error
    except (OverflowError, ArithmeticError) as error:
        raise ValueError("Operación fuera de rango o no válida.") from error


def formato(valor):
    if abs(valor) < 1e-12:
        return "0"
    if abs(valor) < 1e15 and valor == int(valor):
        return str(int(valor))
    return f"{valor:.12g}"


# --------------------------- INTERFAZ WEB ---------------------------
st.set_page_config(
    page_title="Calculadora científica",
    page_icon="🧮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  .stApp {
      background: linear-gradient(140deg, #081328 0%, #0e2347 55%, #142b5d 100%);
      color: #eef5ff;
  }
  .block-container {max-width: 760px; padding-top: 2rem; padding-bottom: 3rem;}
  .titulo {
      color: #ffffff; font-size: clamp(2rem, 4vw, 2.8rem);
      font-weight: 800; letter-spacing: -0.04em;
      margin-bottom: 0.15rem; text-align: center;
  }
  .subtitulo {color: #a9c4eb; text-align: center; margin-bottom: 1.6rem;}
  div[data-testid="stTextInput"] input {
      font-size: 1.75rem; font-weight: 650; text-align: right;
      background-color: #edf5ff; color: #10223c;
      border: 2px solid #477cba; border-radius: 13px;
      min-height: 68px;
  }
  div[data-testid="stButton"] button {
      width: 100%; min-height: 3.35rem;
      background: #213a63; color: #f7faff;
      font-size: 1.04rem; font-weight: 650;
      border: 1px solid #375884; border-radius: 11px;
  }
  div[data-testid="stButton"] button:hover {
      color: white; background: #315b91; border-color: #93c5fd;
  }
  div[data-testid="stButton"] button[kind="primary"] {
      background: #20a596; color: #ffffff; border: 1px solid #23c6b2;
  }
  div[data-testid="stButton"] button[kind="primary"]:hover {background: #178b80;}
  .resultado {
      border: 1px solid #2c5685; border-radius: 13px;
      background: rgba(6, 20, 42, .75);
      padding: 14px 18px; text-align: right; margin: 10px 0 14px;
  }
  .etiqueta {font-size: .85rem; color: #a5c8f5; margin-bottom: .25rem;}
  .numero {font-size: 1.8rem; color: #78f7e6; font-weight: 800; overflow-wrap: anywhere;}
  .nota {color: #bfd4ee; font-size: .87rem; text-align: center; margin-top: 18px;}
  [data-testid="stAlert"] {border-radius: 12px;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="titulo">🧮 Calculadora científica</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitulo">Operaciones matemáticas con Python y Streamlit</div>',
    unsafe_allow_html=True,
)

for clave, valor in {
    "expresion": "",
    "resultado": "0",
    "mensaje_error": "",
    "ans": 0,
    "historial": [],
    "modo": "Grados",
    "recien_calculado": False,
}.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor


def presionar(boton):
    expresion = st.session_state.expresion
    st.session_state.mensaje_error = ""

    if boton == "C":
        st.session_state.expresion = ""
        st.session_state.resultado = "0"
        st.session_state.recien_calculado = False
        return
    if boton == "⌫":
        st.session_state.expresion = expresion[:-1]
        st.session_state.recien_calculado = False
        return
    if boton == "=":
        try:
            valor = calcular_expresion(
                expresion,
                modo_grados=(st.session_state.modo == "Grados"),
                ans=st.session_state.ans,
            )
            salida = formato(valor)
            st.session_state.resultado = salida
            st.session_state.ans = valor
            st.session_state.historial.insert(0, (expresion, salida))
            st.session_state.historial = st.session_state.historial[:8]
            st.session_state.expresion = salida
            st.session_state.recien_calculado = True
        except ValueError as error:
            st.session_state.mensaje_error = str(error)
        return

    if boton == "±":
        st.session_state.expresion = f"-({expresion})" if expresion else "-"
        st.session_state.recien_calculado = False
        return
    if boton == "x²":
        st.session_state.expresion = f"({expresion})**2" if expresion else ""
        st.session_state.recien_calculado = False
        return
    if boton == "1/x":
        st.session_state.expresion = f"1/({expresion})" if expresion else "1/("
        st.session_state.recien_calculado = False
        return
    if boton == "n!":
        st.session_state.expresion = f"fact({expresion})" if expresion else "fact("
        st.session_state.recien_calculado = False
        return
    if boton == "|x|":
        st.session_state.expresion = f"abs({expresion})" if expresion else "abs("
        st.session_state.recien_calculado = False
        return

    sustituciones = {
        "÷": "/", "×": "*", "−": "-", "xʸ": "**",
        "π": "pi", "Ans": "ans", "%": "/100",
        "√": "sqrt(", "exp": "exp(",
        "sin": "sin(", "cos": "cos(", "tan": "tan(",
        "asin": "asin(", "acos": "acos(", "atan": "atan(",
        "ln": "ln(", "log": "log(",
    }
    texto = sustituciones.get(boton, boton)

    if st.session_state.recien_calculado and (boton.isdigit() or boton == "."):
        expresion = ""
    st.session_state.recien_calculado = False

    if boton in ("+", "−", "×", "÷", "xʸ"):
        if not expresion and boton != "−":
            return
        # Reemplazar operadores consecutivos al pulsar otro operador.
        if expresion.endswith(("+", "-", "*", "/")):
            expresion = expresion.rstrip("+-*/")
            if not expresion and boton != "−":
                return

    if boton == ".":
        ultimo = re.split(r"[+\-*/()]", expresion)[-1]
        if "." in ultimo:
            return
        if ultimo == "":
            texto = "0."

    # Multiplicación implícita para expresiones como 2π, 2sin(30) o 2(3+4).
    if texto in ("pi", "e", "ans", "(") or texto.endswith("("):
        if expresion and (expresion[-1].isdigit() or expresion.endswith((")", "pi", "ans"))):
            expresion += "*"
    if texto[0].isdigit() and expresion.endswith((")", "pi", "ans")):
        expresion += "*"

    if len(expresion + texto) <= 180:
        st.session_state.expresion = expresion + texto


st.radio(
    "Modo trigonométrico",
    ["Grados", "Radianes"],
    key="modo",
    horizontal=True,
    help="En grados, sin(30) devuelve 0.5. En radianes usa valores como sin(pi/2).",
)

st.text_input(
    "Expresión matemática (también puedes escribir con tu teclado)",
    key="expresion",
    placeholder="Ejemplo: sqrt(81) + sin(30)",
)

resultado_seguro = html.escape(st.session_state.resultado)
st.markdown(
    f'<div class="resultado"><div class="etiqueta">RESULTADO</div>'
    f'<div class="numero">{resultado_seguro}</div></div>',
    unsafe_allow_html=True,
)
if st.session_state.mensaje_error:
    st.error(st.session_state.mensaje_error)

filas = [
    ["C", "⌫", "(", ")", "÷"],
    ["sin", "cos", "tan", "ln", "log"],
    ["asin", "acos", "atan", "√", "x²"],
    ["7", "8", "9", "×", "xʸ"],
    ["4", "5", "6", "−", "n!"],
    ["1", "2", "3", "+", "%"],
    ["0", ".", "π", "e", "="],
    ["Ans", "±", "1/x", "exp", "|x|"],
]

for indice_fila, fila in enumerate(filas):
    columnas = st.columns(5, gap="small")
    for indice_columna, boton in enumerate(fila):
        with columnas[indice_columna]:
            st.button(
                boton,
                key=f"boton_{indice_fila}_{indice_columna}",
                use_container_width=True,
                type="primary" if boton == "=" else "secondary",
                on_click=presionar,
                args=(boton,),
            )

with st.expander("📘 ¿Cómo utilizar las funciones científicas?"):
    st.markdown(
        """
- **Seno:** `sin(30)` → 0.5 en modo grados.
- **Coseno y tangente:** `cos(60)` y `tan(45)`.
- **Raíz cuadrada:** `sqrt(81)` → 9.
- **Potencia:** `2**3` → 8, o pulsa **xʸ**.
- **Logaritmos:** `log(100)` → 2; `ln(e)` → 1.
- **Factorial:** escribe `5` y pulsa **n!** → 120.
- **Porcentaje:** `25%` mediante botones se escribe `25/100` → 0.25.
- **Constantes:** `pi` y `e`.
- **Respuesta anterior:** pulsa **Ans** o escribe `ans`.
- **Paréntesis:** cierra el paréntesis de funciones como `sqrt(` antes de pulsar **=**.
- **Decimales:** usa el punto (`2.5`), no la coma.
        """
    )

if st.session_state.historial:
    with st.expander("🕘 Historial de operaciones"):
        for operacion, valor in st.session_state.historial:
            st.code(f"{operacion} = {valor}", language=None)

st.markdown(
    '<div class="nota">Hecha con Python · Streamlit · Lista para compartir desde GitHub</div>',
    unsafe_allow_html=True,
)
