import streamlit as st
import pandas as pd
import plotly.express as px
from datasets import load_dataset
import logging
import aiohttp
import io
import asyncio

# Настройка логирования
logging.basicConfig(
    filename="app.log", 
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("streamlit_logger")
logger.info("Приложение запущено.")

# Streamlit UI
st.title("Dataset EDA and Inference App")
logger.info("UI загружен.")


async def send_file_to_server(file):
    try:
        # Создаем асинхронную сессию для отправки данных
        async with aiohttp.ClientSession() as session:
            url = "http://speechgpt:8000/predict"
            data = aiohttp.FormData()
            data.add_field('file', file, filename='audio.wav', content_type='audio/wav')

            async with session.post(url, data=data, timeout=600) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Ошибка от сервера: {response.status}"}
    except asyncio.TimeoutError:
        return {"error": "Сервер не ответил в течение 10 минут."}
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        return {"error": f"Ошибка при отправке файла: {e}"}


st.write("### Загрузка файла для инференса")
uploaded_file = st.file_uploader("Загрузите файл для отправки на сервер SpeechGPT", type=["wav", "mp3", "flac"])

if uploaded_file is not None:
    logger.info(f"Файл загружен: {uploaded_file.name}")
    st.write("Отправка файла на сервер. Время ответа в среднем занимает 3-5 минут, пожалуста, подождите.")

    file_data = io.BytesIO(uploaded_file.read())

    response_data = asyncio.run(send_file_to_server(file_data))

    if 'error' in response_data:
        st.error(response_data['detail'])
    else:
        st.write(response_data['text'])
        logger.info(f"Ответ от сервера: {response_data}")

# Выбор датасета
dataset_option = st.selectbox(
    "Выберите датасет для анализа",
    ("FSD50K", "AISHELL", "Alpaca", "Audiocaps")
)
logger.info(f"Выбран датасет: {dataset_option}")

try:
    if dataset_option == "FSD50K":
        logger.info("Загрузка FSD50K dataset...")
        ds = load_dataset("CLAPv2/FSD50K")['train']
        df = pd.DataFrame(ds)
        st.write("### EDA для FSD50K")
        st.write(df.head())
        logger.info(f"Размер данных FSD50K: {df.shape}")

        # Графики
        fig = px.histogram(df, x="audio_len", title="Распределение длительности аудио")
        st.plotly_chart(fig)
        logger.info("Гистограмма аудио длительности создана.")

    elif dataset_option == "AISHELL":
        logger.info("Загрузка AISHELL dataset...")
        ds = load_dataset("DynamicSuperbPrivate/SpeakerVerification_Aishell1Train")['train']
        df = pd.DataFrame(ds)
        st.write("### EDA для AISHELL")
        st.write(df.head())
        logger.info(f"Размер данных AISHELL: {df.shape}")

        # Графики
        fig = px.histogram(df, x="label", title="Распределение меток")
        st.plotly_chart(fig)
        logger.info("Гистограмма меток создана.")

    elif dataset_option == "Alpaca":
        logger.info("Загрузка Alpaca dataset...")
        ds = load_dataset("yahma/alpaca-cleaned")['train']
        df = pd.DataFrame(ds) 
        st.write("### EDA для Alpaca")
        st.write(df.head())
        logger.info(f"Размер данных Alpaca: {df.shape}")

        # Графики 
        fig = px.histogram(df, x="instruction", title="Распределение инструкций")
        st.plotly_chart(fig)
        logger.info("Гистограмма инструкций создана.")

    elif dataset_option == "Audiocaps":
        logger.info("Загрузка Audiocaps dataset...")
        ds = load_dataset("d0rj/audiocaps")['train']
        df = pd.DataFrame(ds)
        st.write("### EDA для Audiocaps")
        st.write(df.head())
        logger.info(f"Размер данных Audiocaps: {df.shape}")

        # Графики
        fig = px.histogram(df, x="start_time", title="Распределение начальных времен аудиоклипов")
        st.plotly_chart(fig)
        logger.info("Гистограмма начальных времен аудиоклипов создана.")

    # Инференс семпла
    st.write("### Инференс семпла")
    selected_sample = st.number_input("Выберите индекс семпла", min_value=0, step=1, value=0)
    if st.button("Инференс семпла"):
        sample = df.iloc[selected_sample]
        st.write("Выбранный семпл:", sample)
        logger.info(f"Инференс семпла: {sample}")

except Exception as e:
    logger.error(f"Ошибка: {e}")
    st.error(f"Произошла ошибка: {e}")

st.write("Приложение завершило работу.")
logger.info("Приложение завершено.")
