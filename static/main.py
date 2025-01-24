import tkinter as tk
import tkinter.ttk
from tkinter import ttk, filedialog
from ttkbootstrap import Style
from PIL import Image, ImageTk
import cv2
from ttkbootstrap.widgets import Meter
import pandas as pd
from ultralytics import YOLO
from tracker import Tracker
from ttkbootstrap.widgets import DateEntry
from datetime import datetime
import os
import sqlite3
from fpdf import FPDF

def main():
    # Configurar a janela principal
    root = tk.Tk()
    root.title("Yolo")
    root.geometry("800x600")

    # Carregar a imagem da logo
    logo_image = Image.open("yolo.png")
    logo_image = logo_image.resize((20, 20), Image.Resampling.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_image)

    # Configurar a logo na barra da janela
    root.iconphoto(False, logo_photo)

    # Aplicar o tema
    style = Style()
    valid_theme = 'superhero' if 'superhero' in style.theme_names() else style.theme_names()[0]
    style.theme_use(valid_theme)

    # Criar o frame principal
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Criar o notebook para adicionar abas
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True, padx=(0, 0))

    # Criar a aba Camera 1
    camera_frame = ttk.Frame(notebook)
    notebook.add(camera_frame, text="Camera 1")

    # Criar a aba Configurações
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text="Relatórios")

    # Conteúdo da aba Camera 1
    content_frame = ttk.Frame(camera_frame)
    content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Variáveis para controle de desenho
    drawing = [False]
    start_x = [0]
    start_y = [0]
    detection_bars = [None, None]  # Armazenar coordenadas das duas barras de detecção
    current_bar = tk.IntVar(value=0)  # Variável de controle para saber qual barra desenhar (0 para Up, 1 para Down)

    # Criar ou conectar ao banco de dados SQLite
    conn = sqlite3.connect('contagem_pessoas.db')

    # Criar um cursor para executar comandos SQL
    cursor = conn.cursor()

    # Criar a tabela contagem se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contagem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            hora TEXT,
            objeto TEXT,
            qtd INTEGER
        )
    ''')

    # Salvar as mudanças no banco de dados
    conn.commit()

    # Barra de buscar
    video_source_entry = ttk.Entry(content_frame, width=65)
    video_source_entry.place(x=105, y=10)

    # Variáveis para controle de desenho
    drawing = [False]
    start_x = [0]
    start_y = [0]
    detection_bars = [None, None]  # Armazenar coordenadas das duas barras de detecção
    current_bar = tk.IntVar(value=0)  # Variável de controle para saber qual barra desenhar (0 para Up, 1 para Down)

    # Criar ou conectar ao banco de dados SQLite
    conn = sqlite3.connect('contagem_pessoas.db')

    # Criar um cursor para executar comandos SQL
    cursor = conn.cursor()

    # Criar a tabela contagem se não existir
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS contagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                hora TEXT,
                objeto TEXT,
                qtd INTEGER
            )
        ''')

    # Salvar as mudanças no banco de dados
    conn.commit()

    # Criar o frame de filtros na aba Relatórios
    filter_frame = ttk.Frame(settings_frame)
    filter_frame.pack(fill=tk.X, padx=10, pady=10)

    # Adicionar widgets ao frame de filtros
    start_date_label = ttk.Label(filter_frame, text="Período", bootstyle="readonly")
    start_date_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    end_date_entry = DateEntry(filter_frame, bootstyle="readonly", width=12)
    end_date_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

    model_label = ttk.Label(filter_frame, text="Modelo", bootstyle="primary")
    model_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")

    model_combobox = ttk.Combobox(filter_frame, values=["Pessoas", "Automóveis", "Objetos"], state="readonly",
                                  bootstyle="primary", width=12)
    model_combobox.grid(row=0, column=3, padx=10, pady=10, sticky="w")
    model_combobox.set("Pessoas")

    # Definir o botão de busca com um estilo mais moderno
    search_button = ttk.Button(filter_frame, text="Buscar", bootstyle="primary-outline")
    search_button.grid(row=0, column=4, padx=10, pady=10, sticky="w")

    # Criar o frame da tabela de resultados
    table_frame = ttk.Frame(settings_frame)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Adicionar uma frame interna para a Treeview e Scrollbar
    inner_frame = ttk.Frame(table_frame)
    inner_frame.pack(fill=tk.BOTH, expand=True)

    columns = ('data', 'horario', 'objeto', 'qtd', 'excluir')
    table = ttk.Treeview(inner_frame, columns=columns, show='headings', bootstyle="info")

    # Definir os cabeçalhos da tabela com um estilo mais moderno
    table.heading('data', text='Data', anchor='center')
    table.heading('horario', text='Horário', anchor='center')
    table.heading('objeto', text='Objeto', anchor='center')
    table.heading('qtd', text='QTD', anchor='center')
    table.heading('excluir', text='', anchor='center')

    # Configurar as colunas da tabela com alinhamento centralizado
    table.column('data', width=120, anchor='center')
    table.column('horario', width=120, anchor='center')
    table.column('objeto', width=100, anchor='center')
    table.column('qtd', width=50, anchor='center')
    table.column('excluir', width=70, anchor='center')

    # Estilizar as linhas da tabela para alternar entre cores e adicionar separadores
    table.tag_configure('evenrow', background='#f0f0f0')
    table.tag_configure('oddrow', background='#ffffff')
    table.tag_configure('separator', background='#d9d9d9', font=('TkDefaultFont', 1))  # Linha separadora com altura 1

    # Adicionar o Scrollbar vertical usando o ttkbootstrap
    scrollbar = ttk.Scrollbar(inner_frame, orient=tk.VERTICAL, command=table.yview, bootstyle="primary-round")
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Conectar o Treeview com o Scrollbar
    table.configure(yscrollcommand=scrollbar.set)

    # Colocar a tabela e o scrollbar juntos
    table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Função para buscar e mostrar dados
    def buscar_dados():
        # Limpar a tabela antes de inserir novos dados
        for row in table.get_children():
            table.delete(row)

        # Obter a data e modelo selecionados pelo usuário
        try:
            data = end_date_entry.get_date().strftime('%Y-%m-%d')
        except AttributeError:
            data = end_date_entry.entry.get()  # Tentativa de fallback para o método entry.get()

        modelo = model_combobox.get()

        # Consultar o banco de dados para obter os dados filtrados
        cursor.execute('''
                SELECT data, hora, objeto, qtd FROM contagem
                WHERE data = ? AND objeto = ?
            ''', (data, modelo))

        # Obter todos os resultados da consulta
        rows = cursor.fetchall()

        # Inserir os dados na tabela
        for i, row in enumerate(rows):
            table.insert('', tk.END, values=row, tags=('evenrow' if i % 2 == 0 else 'oddrow'))

            # Inserir uma linha separadora após cada grupo de dados
            table.insert('', tk.END, values=("", "", "", "", ""), tags=('separator',))

    # Associa a função ao botão Buscar
    search_button.config(command=buscar_dados)

    def save_data():
        # Capturar os valores de data, hora, objeto e quantidade
        data = datetime.now().strftime('%Y-%m-%d')  # Data atual
        hora = datetime.now().strftime('%H:%M:%S')  # Hora atual
        objeto = model_combobox.get()  # Objeto selecionado no Combobox
        qtd = meter1['amountused']  # Quantidade de pessoas (total)

        # Inserir os dados na tabela contagem
        cursor.execute('''
            INSERT INTO contagem (data, hora, objeto, qtd)
            VALUES (?, ?, ?, ?)
        ''', (data, hora, objeto, qtd))

        # Salvar as mudanças no banco de dados
        conn.commit()

        # Exibir uma mensagem de confirmação (opcional)
        print(f"Dados gravados: Data={data}, Hora={hora}, Objeto={objeto}, Quantidade={qtd}")

        # Associar a função `save_data` ao botão 'Gravar'
    save_mod_button = ttk.Button(camera_frame, text="Gravar", command=save_data)
    save_mod_button.place(x=598, y=440, width=100)

    def exportar_pdf():
        # Criar um objeto PDF
        pdf = FPDF()
        pdf.add_page()

        # Definir a fonte
        pdf.set_font("Arial", size=12)

        # Título do PDF
        pdf.cell(200, 10, txt="Relatório de Contagem de Objetos", ln=True, align='C')

        # Espaço entre título e o conteúdo
        pdf.ln(10)

        # Adicionar os dados da tabela no PDF
        pdf.set_font("Arial", size=10)
        pdf.cell(40, 10, "Data", 1)
        pdf.cell(40, 10, "Horário", 1)
        pdf.cell(60, 10, "Objeto", 1)
        pdf.cell(20, 10, "Quantidade", 1)
        pdf.ln()

        for row in table.get_children():
            values = table.item(row, "values")
            pdf.cell(40, 10, values[0], 1)
            pdf.cell(40, 10, values[1], 1)
            pdf.cell(60, 10, values[2], 1)
            pdf.cell(20, 10, values[3], 1)
            pdf.ln()

        # Salvar o PDF
        filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if filename:
            pdf.output(filename)

    # Adicionar o botão "Exportar" na aba Relatórios
    export_button = ttk.Button(filter_frame, text="Exportar PDF", bootstyle="secondary", command=exportar_pdf)
    export_button.grid(row=0, column=5, padx=10, pady=10, sticky="w")

    # Função para carregar o vídeo
    def load_video():
        video_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4;*.avi")])
        video_source_entry.delete(0, tk.END)
        video_source_entry.insert(0, video_path)
        return video_path

    # Variável de controle para o loop de contagem
    running = [True]

    # Dicionário para rastrear quais IDs já cruzaram a linha
    crossed_ids = set()

    # Função para reproduzir o vídeo e realizar a contagem de pessoas
    def play_video(video_path):
        model = YOLO('yolov8s.pt')
        cap = cv2.VideoCapture(video_path)

        my_file = open("coco.txt", "r")
        data = my_file.read()
        class_list = data.split("\n")

        count = 0
        tracker = Tracker()
        people_count_up = 0
        people_count_down = 0

        last_positions = {}  # Dicionário para armazenar a última posição (y) de cada pessoa detectada

        while running[0]:
            ret, frame = cap.read()
            if not ret:
                break

            count += 1
            if count % 3 != 0:
                continue
            frame = cv2.resize(frame, (500, 400))

            results = model.predict(frame)
            a = results[0].boxes.data
            px = pd.DataFrame(a).astype("float")

            list_bbox = []
            for index, row in px.iterrows():
                x1 = int(row[0])
                y1 = int(row[1])
                x2 = int(row[2])
                y2 = int(row[3])
                d = int(row[5])
                c = class_list[d]
                if 'person' in c:
                    list_bbox.append([x1, y1, x2, y2])

            bbox_id = tracker.update(list_bbox)
            for bbox in bbox_id:
                x3, y3, x4, y4, id = bbox
                cx = (x3 + x4) // 2
                cy = (y3 + y4) // 2

                # Desenhar as barras de detecção na tela do vídeo
                for i, bar in enumerate(detection_bars):
                    if bar is not None:
                        x1, y1, x2, y2 = bar
                        color = (0, 255, 255) if i == 0 else (
                        0, 255, 0)  # Amarelo para a primeira barra, verde para a segunda
                        cv2.line(frame, (x1, y1), (x2, y2), color, 2)

                # Verificação de contagem com base nas barras de detecção desenhadas
                color = (0, 0, 255)  # Cor vermelha padrão para pessoas que ainda não cruzaram uma barra

                if id in last_positions:
                    previous_y = last_positions[id]

                    # Verificação para a barra de detecção amarela (movimento de cima para baixo)
                    if detection_bars[0] is not None:
                        x1, y1, x2, y2 = detection_bars[0]
                        if previous_y < y1 and cy >= y1:  # A pessoa estava acima da barra e agora está na barra ou abaixo
                            people_count_up += 1
                            color = (0, 255, 255)  # Cor amarela para pessoas que cruzaram a primeira barra

                    # Verificação para a barra de detecção verde (movimento de baixo para cima)
                    if detection_bars[1] is not None:
                        x1, y1, x2, y2 = detection_bars[1]
                        if previous_y > y2 and cy <= y2:  # A pessoa estava abaixo da barra e agora está na barra ou acima
                            people_count_down += 1
                            color = (0, 255, 0)  # Cor verde para pessoas que cruzaram a segunda barra

                # Atualizar a posição da pessoa
                last_positions[id] = cy

                # Desenhar o retângulo ao redor da pessoa detectada com a cor apropriada
                cv2.rectangle(frame, (x3, y3), (x4, y4), color, 2)

                # Exibir as contagens na tela
                cv2.putText(frame, f"Count Up: {people_count_up}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255),
                            2)
                cv2.putText(frame, f"Count Down: {people_count_down}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1,
                            (0, 255, 0), 2)

            # Atualizar os meters
            meter1.configure(amountused=people_count_up + people_count_down)
            meter2.configure(amountused=people_count_up)
            meter3.configure(amountused=people_count_down)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            canvas.create_image(0, 0, anchor=tk.NW, image=img)
            canvas.image = img
            canvas.update()

        cap.release()

    def stop_counting():
        running[0] = False

    def start_draw(event):
        drawing[0] = True
        start_x[0] = event.x
        start_y[0] = event.y

    def end_draw(event):
        if drawing[0]:
            drawing[0] = False
            end_x = event.x
            end_y = event.y
            if current_bar.get() == 0:
                detection_bars[0] = (start_x[0], start_y[0], end_x, end_y)
                canvas.create_line(start_x[0], start_y[0], end_x, end_y, fill="yellow", width=2)
            elif current_bar.get() == 1:
                detection_bars[1] = (start_x[0], start_y[0], end_x, end_y)
                canvas.create_line(start_x[0], start_y[0], end_x, end_y, fill="green", width=2)

    def start_counting():
        video_path = video_source_entry.get()
        if video_path:
            running[0] = True
            play_video(video_path)

    def clear_bars():
        detection_bars[0] = None
        detection_bars[1] = None
        canvas.delete("all")
        canvas.create_rectangle(0, 0, 500, 400, fill="blue")

    overlay_frame = ttk.Labelframe(content_frame, text="Pessoas", labelanchor='n', width=240, height=500)
    overlay_frame.place(x=520, y=3)

    # Botão para carregar o vídeo
    load_video_button = ttk.Button(content_frame, text="Search Vídeo", command=load_video)
    load_video_button.place(x=10, y=10)

    canvas = tk.Canvas(content_frame, width=500, height=400, bg="black")
    canvas.place(x=10, y=50)

    start_button = ttk.Checkbutton(content_frame, bootstyle="toolbutton", text="Iniciar", command=start_counting)
    start_button.place(x=588, y=360, width=100)

    stop_button = ttk.Button(content_frame, text="Parar", command=stop_counting)
    stop_button.place(x=588, y=395, width=100)

    # Meters
    meter1 = Meter(content_frame,
                   subtext="Total",
                   textright="%",
                   metersize=200,  # Aumenta o tamanho do meter para maior destaque
                   amounttotal=100,
                   amountused=0,
                   metertype="full",
                   stripethickness=6,  # Aumenta a espessura das listras para um visual mais robusto
                   wedgesize=8,  # Aumenta o tamanho das divisões para uma aparência mais definida
                   interactive=False,
                   bootstyle='danger-gradient',  # Aplica um gradiente para um visual mais moderno
                   textfont="Helvetica 24 bold",  # Usa uma fonte mais moderna e com maior destaque
                   subtextfont="Helvetica 14 italic",  # Usa uma fonte mais elegante para o subtítulo
                   )
    meter1.place(x=540, y=30)

    meter2 = Meter(content_frame,
                   subtext="Count Up",
                   textright="%",
                   metersize=110,
                   amounttotal=100,
                   amountused=0,
                   metertype="full",
                   stripethickness=4,
                   wedgesize=5,
                   interactive=False,
                   bootstyle='success',  # Define o estilo com cor verde
                   textfont="TkDefaultFont 10 bold",
                   subtextfont="TkDefaultFont 8")
    meter2.place(x=528, y=240)

    meter3 = Meter(content_frame,
                   subtext="Count Down",
                   textright="P",
                   metersize=110,
                   amounttotal=100,
                   amountused=0,
                   metertype="full",
                   stripethickness=4,
                   wedgesize=5,
                   interactive=False,
                   bootstyle='success',  # Define o estilo com cor verde
                   textfont="TkDefaultFont 10 bold",
                   subtextfont="TkDefaultFont 8")
    meter3.place(x=643, y=240)

    def activate_drawing_mode():
        canvas.bind("<Button-1>", start_draw)
        canvas.bind("<ButtonRelease-1>", end_draw)

    new_model_button = ttk.Button(content_frame, text="Criar barras", command=activate_drawing_mode)
    new_model_button.place(x=10, y=475, width=100)

    clear_button = ttk.Button(content_frame, text="Limpar Barras", command=clear_bars)
    clear_button.place(x=118, y=475, width=100)

    clear_combobox = ttk.Combobox(content_frame, values=["Pessoas", "Automóveis"], state="readonly")
    clear_combobox.place(x=408, y=475, width=100)

    # Adicionar Radiobuttons para selecionar a barra a ser desenhada
    radio_up = ttk.Radiobutton(content_frame, text="Up", variable=current_bar, value=0)
    radio_up.place(x=230, y=483)

    radio_down = ttk.Radiobutton(content_frame, text="Down", variable=current_bar, value=1)
    radio_down.place(x=270, y=483)

    root.mainloop()

if __name__ == "__main__":
    main()