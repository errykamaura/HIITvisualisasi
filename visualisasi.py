import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env dari folder file ini berada
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Ambil MONGO_URI dari environment variable atau .env
MONGO_URI = os.getenv("MONGO_URI")

# Debug: tampilkan nilai MONGO_URI
st.write(f"MONGO_URI = {MONGO_URI}")

if not MONGO_URI:
    st.error("MONGO_URI tidak ditemukan di environment variable atau file .env!")
    st.stop()

# Koneksi MongoDB
client = MongoClient(MONGO_URI)
db = client['capstone']
collection = db['visualisasi2']

# === Fungsi Sinkronisasi Data ===
def sync_exercise_data():
    try:
        categories = requests.get('https://wger.de/api/v2/exercisecategory/').json()['results']
        category_dict = {cat['id']: cat['name'] for cat in categories}

        equipments = requests.get('https://wger.de/api/v2/equipment/').json()['results']
        equipment_dict = {eq['id']: eq['name'] for eq in equipments}

        muscles = requests.get('https://wger.de/api/v2/muscle/').json()['results']
        muscle_dict = {muscle['id']: muscle['name'] for muscle in muscles}

        all_exercises = []
        next_url = 'https://wger.de/api/v2/exerciseinfo/?limit=100&language=2'

        while next_url:
            response = requests.get(next_url)
            data = response.json()
            all_exercises.extend(data['results'])
            next_url = data['next']

        total_saved = 0
        now = datetime.utcnow()

        for exercise in all_exercises:
            exercise['category_name'] = category_dict.get(exercise.get('category', {}).get('id'), 'Unknown')
            exercise['equipment_names'] = [equipment_dict.get(eq.get('id'), 'Unknown') for eq in exercise.get('equipment', [])]
            exercise['muscle_names'] = [muscle_dict.get(m.get('id'), 'Unknown') for m in exercise.get('muscles', [])]
            exercise['muscle_secondary_names'] = [muscle_dict.get(m.get('id'), 'Unknown') for m in exercise.get('muscles_secondary', [])]
            exercise['last_synced'] = now

            if not exercise.get('name'):
                exercise['name'] = 'No Name'

            collection.replace_one({'id': exercise['id']}, exercise, upsert=True)
            total_saved += 1

        return total_saved

    except Exception as e:
        return f"❌ Error: {e}"

# === Streamlit UI ===
st.set_page_config(page_title="WGER Exercise Sync App", layout="wide")
st.title("💪 WGER Exercise Sync App")

# Tombol Sinkronisasi
if st.button("🔄 Sinkronisasi Data Latihan"):
    result = sync_exercise_data()
    if isinstance(result, int):
        st.success(f"✅ Sinkronisasi berhasil. Total data disimpan: {result}")
    else:
        st.error(result)

# Tampilkan Semua Latihan
if st.button("📋 Tampilkan Semua Latihan"):
    data = list(collection.find().sort("name", 1))
    if data:
        for item in data:
            st.subheader(item['name'])
            st.write(f"Kategori: {item.get('category_name', 'Unknown')}")
            st.write(f"Peralatan: {', '.join(item.get('equipment_names', []))}")
            st.write(f"Otot Utama: {', '.join(item.get('muscle_names', []))}")
            st.write(f"Otot Sekunder: {', '.join(item.get('muscle_secondary_names', []))}")
            st.markdown("---")
    else:
        st.warning("Belum ada data latihan tersimpan.")

# === Visualisasi Data ===
# === Visualisasi Data ===
st.header("📊 Visualisasi Data Latihan")

if st.button("📈 Tampilkan Visualisasi"):
    data = list(collection.find())
    if not data:
        st.warning("Belum ada data untuk divisualisasikan.")
    else:
        df = pd.DataFrame(data)

        # Pastikan kolom ada
        if 'category_name' not in df.columns or 'equipment_names' not in df.columns or 'muscle_names' not in df.columns:
            st.error("Data belum lengkap: Pastikan semua kolom (category_name, equipment_names, muscle_names) tersedia.")
        else:
            # Visualisasi 1: Latihan per Kategori
            st.subheader("Jumlah Latihan per Kategori")
            kategori_count = df['category_name'].value_counts().reset_index()
            kategori_count.columns = ['Kategori', 'Jumlah Latihan']

            # Tabel rapi
            st.dataframe(
                kategori_count.style.set_properties(**{'text-align': 'center'}).set_table_styles([{
                    'selector': 'th',
                    'props': [('text-align', 'center')]
                }])
            )

            # Grafik
            fig1, ax1 = plt.subplots(figsize=(10, 5))
            kategori_count.set_index('Kategori')['Jumlah Latihan'].plot(kind='bar', ax=ax1, color='skyblue')
            ax1.set_title("Distribusi Latihan Berdasarkan Kategori")
            ax1.set_xlabel("Kategori")
            ax1.set_ylabel("Jumlah Latihan")
            ax1.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            st.pyplot(fig1)

            st.markdown("---")

            # Visualisasi 2: Latihan per Peralatan (Top 10)
            st.subheader("Jumlah Latihan per Peralatan (Top 10)")
            equipment_series = df['equipment_names'].explode()
            equipment_count = equipment_series.value_counts().head(10).reset_index()
            equipment_count.columns = ['Peralatan', 'Jumlah Latihan']

            # Tabel rapi
            st.dataframe(
                equipment_count.style.set_properties(**{'text-align': 'center'}).set_table_styles([{
                    'selector': 'th',
                    'props': [('text-align', 'center')]
                }])
            )

            # Grafik
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            equipment_count.set_index('Peralatan')['Jumlah Latihan'].plot(kind='bar', ax=ax2, color='orange')
            ax2.set_title("Top 10 Peralatan yang Digunakan")
            ax2.set_xlabel("Peralatan")
            ax2.set_ylabel("Jumlah Latihan")
            ax2.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            st.pyplot(fig2)

            st.markdown("---")

            # Visualisasi 3: Latihan per Otot Utama (Top 10)
            st.subheader("Jumlah Latihan per Otot Utama (Top 10)")
            muscle_series = df['muscle_names'].explode()
            muscle_count = muscle_series.value_counts().head(10).reset_index()
            muscle_count.columns = ['Otot Utama', 'Jumlah Latihan']

            # Tabel rapi
            st.dataframe(
                muscle_count.style.set_properties(**{'text-align': 'center'}).set_table_styles([{
                    'selector': 'th',
                    'props': [('text-align', 'center')]
                }])
            )

            # Grafik
            fig3, ax3 = plt.subplots(figsize=(10, 5))
            muscle_count.set_index('Otot Utama')['Jumlah Latihan'].plot(kind='bar', ax=ax3, color='green')
            ax3.set_title("Top 10 Otot Utama yang Dilatih")
            ax3.set_xlabel("Otot")
            ax3.set_ylabel("Jumlah Latihan")
            ax3.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            st.pyplot(fig3)
