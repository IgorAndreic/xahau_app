from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

app.config['SECRET_KEY'] = 'xfbx85*x8fxc0xcax9axedxcabx1a+Tx9e8tZdx84xce'
# Словарь для хранения процессов
processes = {}

@app.route('/')
def index():
    return render_template('index.html', processes=processes)

@app.route('/start/<script_name>')
def start_script(script_name):
    if script_name not in processes:
        processes[script_name] = subprocess.Popen(['python3', f'/home/xahau/src/{script_name}.py'])
        logging.info(f'Скрипт {script_name}.py запущен.')
        flash(f'Скрипт {script_name}.py запущен.')
    else:
        flash(f'Скрипт {script_name}.py уже запущен.')
    return redirect(url_for('index'))

@app.route('/stop/<script_name>')
def stop_script(script_name):
    if script_name in processes:
        processes[script_name].terminate()  # Останавливаем процесс
        del processes[script_name]  # Удаляем процесс из словаря
        flash(f'Скрипт {script_name} был успешно остановлен.', 'success')
    else:
        flash(f'Скрипт {script_name} не найден среди запущенных процессов.', 'error')
    return redirect(url_for('index'))

@app.route('/restart/<script_name>')
def restart_script(script_name):
    message_type = 'success'
    if script_name in processes:
        processes[script_name].terminate()  # Останавливаем текущий процесс
        del processes[script_name]  # Удаляем процесс из словаря
        processes[script_name] = subprocess.Popen(['python3', f'/home/xahau/src/{script_name}.py'])  # Запускаем процесс заново
        flash_message = f'Скрипт {script_name} был успешно перезапущен.'
    else:
        processes[script_name] = subprocess.Popen(['python3', f'/home/xahau/src/{script_name}.py'])  # Просто запускаем процесс, если он не был запущен
        flash_message = f'Скрипт {script_name} запущен, поскольку он не был запущен ранее.'
        message_type = 'info'
    flash(flash_message, message_type)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)
