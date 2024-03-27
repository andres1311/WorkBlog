from flask import Flask, render_template, request, session, redirect, url_for,abort,make_response
import config
from flask_mysqldb import MySQL
from flask import jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime


app = Flask(__name__)

app.config['SECRET_KEY'] = config.HEX_SEC_KEY
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cur.fetchone()
    cur.close()

    if user is not None:
        session['email'] = email
        session['name'] = user[1]
        session['surnames'] = user[2]

        return redirect(url_for('tasks'))
    else:
        return render_template('index.html', message="Email o contraseña incorrecta")

from flask import abort

@app.route('/tasks', methods=['GET'])
def tasks():
    if 'email' not in session:
        # Si el usuario no ha iniciado sesión, redirige a la página de inicio de sesión
        return redirect(url_for('home'))
    
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tasks WHERE email = %s", [email])
    tasks = cur.fetchall()

    if not tasks:
        # Si no hay tareas, puedes manejarlo de alguna manera, por ejemplo, mostrar un mensaje
        return render_template('tasks.html', message="No hay tareas disponibles.")

    insertObject = []
    columnNames = [column[0] for column in cur.description]
    for record in tasks:
        insertObject.append(dict(zip(columnNames, record)))
    cur.close()

    return render_template('tasks.html', tasks=insertObject)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/new-task', methods=['POST'])
def newTask():
    title = request.form['title']
    description = request.form['description']
    email = session['email']
    d = datetime.now()
    dateTask = d.strftime("%Y-%m-%d %H:%M:%S")

    if title and description and email:
        cur = mysql.connection.cursor()
        sql = "INSERT INTO tasks (email, title, description, date_task) VALUES (%s, %s, %s, %s)"
        data = (email, title, description, dateTask)
        cur.execute(sql, data)
        mysql.connection.commit()
    return redirect(url_for('tasks'))

from flask import flash

@app.route('/new-user', methods=['POST'])
def newUser():
    name = request.form['name']
    surnames = request.form['surnames']
    email = request.form['email']
    password = request.form['password']
    password_confirm = request.form['password_confirm']

    if name and surnames and email and password and password_confirm:
        if password == password_confirm:
            cur = mysql.connection.cursor()
            sql = "INSERT INTO users (name, surnames, email, password) VALUES (%s, %s, %s, %s)"
            data = (name, surnames, email, password)
            cur.execute(sql, data)
            mysql.connection.commit()

            flash('Registro exitoso. Inicia sesión para continuar.', 'success')
        else:
            flash('Las contraseñas no coinciden. Intenta de nuevo.', 'danger')
    else:
        flash('Error en el registro. Completa todos los campos.', 'danger')

    return redirect(url_for('home'))

from flask import redirect, url_for

@app.route('/edit-task', methods=['POST'])
def editTask():
    try:
        # Obtén los datos del formulario
        task_id = request.form['id']
        new_title = request.form['title']
        new_description = request.form['description']

        # Realiza la lógica para editar la tarea en tu base de datos
        cur = mysql.connection.cursor()
        sql = "UPDATE tasks SET title = %s, description = %s WHERE id = %s"
        data = (new_title, new_description, task_id)
        cur.execute(sql, data)
        mysql.connection.commit()
        cur.close()

        # Redirige de vuelta a la página de tareas después de la edición
        return redirect(url_for('tasks'))

    except Exception as e:
        # Devuelve una respuesta de error en formato JSON
        return jsonify(success=False, message=str(e))

@app.route("/delete-task", methods=["POST"])
def deleteTask():
    cur = mysql.connection.cursor()
    id = request.form['id']
    sql = "DELETE FROM tasks WHERE id = %s"
    data = (id,)
    cur.execute(sql, data)
    mysql.connection.commit()
    return redirect(url_for('tasks'))

# Ruta para generar y descargar el PDF de las tareas
@app.route('/generate-pdf')
def generate_pdf():
    if 'email' not in session:
        return redirect(url_for('home'))

    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tasks WHERE email = %s", [email])
    tasks = cur.fetchall()

    if not tasks:
        return render_template('tasks.html', message="No hay tareas disponibles.")

    response = make_response()
    response.headers['Content-Disposition'] = 'attachment; filename=tareas.pdf'
    response.headers['Content-Type'] = 'application/pdf'

    buffer = response.stream
    c = canvas.Canvas(buffer, pagesize=letter)

    # Agregar el encabezado "WorkBlog" centrado en la página
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 750, "WorkBlog")

    # Obtener el nombre y apellido del usuario
    name = session['name']
    surnames = session['surnames']

    # Contar el número de tareas creadas
    num_tasks = len(tasks)

    # Agregar información del usuario y número de tareas creadas
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Buen Dia {name} {surnames}, tienes {num_tasks} tareas creadas.")

    # Comenzar a dibujar las tareas
    y = 700

    for task in tasks:
        # Dibujar el rectángulo
        c.rect(75, y-60, 470, 70, stroke=1, fill=0)

        # Asegúrate de dibujar el texto dentro del rectángulo
        c.drawString(100, y, f"Título: {task[2]}")
        y -= 20
        c.drawString(100, y, f"Descripción: {task[3]}")
        y -= 20
        c.drawString(100, y, f"Fecha: {task[4]}")

        # Espacio adicional antes de la siguiente tarea
        y -= 40

        # Verificar si necesitas una nueva página
        if y < 100:
            c.showPage()
            y = 750  # Restablecer la posición y para la nueva página

    c.showPage()
    c.save()

    return response

if __name__ == '__main__':
    app.run(debug=True)
