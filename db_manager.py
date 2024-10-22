import sqlite3
import sqlitecloud
import json
import logging

logger = logging.getLogger(__name__)

# Function to connect to the database
def connect_db():
	try:	
		conn = sqlitecloud.connect("sqlitecloud://cy9qgtjmhz.sqlite.cloud:8860/main_data.db?apikey=ewyiwIMPWXpLxNvfLdK0IUhUpBwGUuRkB9CTMBeqq5g")
		return conn
	except Exception as e:
		logger.error(f"Error connecting to the database: {e}")
		return None

# Function to create a table for items (run this when bot starts)
def create_item_table():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute('''CREATE TABLE IF NOT EXISTS items (
						id INTEGER PRIMARY KEY,
						item_name TEXT,
						item_aliases TEXT,
						facilities TEXT,
						can_be_crated TEXT,
						can_be_palleted TEXT,
						crate_size TEXT,
						pallet_size TEXT,
						image_url TEXT
					)''')
	conn.commit()
	conn.close()
	
def create_facility_table():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute('''CREATE TABLE IF NOT EXISTS facilities (
						id INTEGER PRIMARY KEY,
						facility_name TEXT,
						facility_aliases TEXT,
						facility_type TEXT,
						image_url TEXT
						)''')
	conn.commit()
	conn.close()
	
def create_stockpile_table():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute('''CREATE TABLE IF NOT EXISTS stockpiles (
						id INTEGER PRIMARY KEY,
						stockpile_name TEXT,
						stockpile_description TEXT,
						stockpile_location TEXT,
						stockpile_passcode INTEGER
						)''')
	conn.commit()
	conn.close()
	
def create_tasks_table():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
						id INTEGER PRIMARY KEY,
						message_id INTEGER,
						channel_id INTEGER,
						item_id TEXT,
						amount INTEGER,
						current_amount INTEGER DEFAULT 0,
						facility_id TEXT,
						stockpile_id TEXT,
						created_by TEXT,
						assigned_users TEXT,
						thumbnail TEXT,
						status TEXT
						)''')
	conn.commit()
	conn.close()

def create_custom_tasks_table():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute('''CREATE TABLE IF NOT EXISTS custom_tasks (
						id INTEGER PRIMARY KEY,
						message_id INTEGER,
						channel_id INTEGER,
						task_header TEXT,
						task_location TEXT,
						task_description TEXT,
						created_by TEXT,
						assigned_users TEXT,
						status TEXT
						)''')
	conn.commit()
	conn.close()

def get_all_task_messages():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT task_id FROM tasks")
	return cursor.fetchall()

# Function to add an item to the database
def add_item_to_db(item_name, item_aliases, facilities, can_be_crated, can_be_palleted, crate_size, pallet_size, image_url):
	conn = connect_db()
	cursor = conn.cursor()
	item_aliases_json = json.dumps(item_aliases)
	facilities_json = json.dumps(facilities)
	cursor.execute("INSERT INTO items (item_name, item_aliases, facilities, can_be_crated, can_be_palleted, crate_size, pallet_size, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
					(item_name, item_aliases_json, facilities_json, can_be_crated, can_be_palleted, crate_size, pallet_size, image_url))
	conn.commit()
	conn.close()
	
#Add facility to database
def add_facility_to_db(facility_name, facility_aliases, facility_type, image_url):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("INSERT INTO facilities (facility_name, facility_aliases, facility_type, image_url) VALUES (?, ?, ?, ?)",
					(facility_name, facility_aliases, facility_type, image_url))
	conn.commit()
	conn.close()
	
def add_stockpile_to_db(stockpile_name, stockpile_description, stockpile_location, stockpile_passcode):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("INSERT INTO stockpiles (stockpile_name, stockpile_description, stockpile_location, stockpile_passcode) VALUES (?, ?, ?, ?)",
					(stockpile_name, stockpile_description, stockpile_location, stockpile_passcode))
	conn.commit()
	conn.close()

def get_facility_from_db(facility_name):
	conn = connect_db()
	cursor = conn.cursor()
	
	# Check if the search term matches either the facility name or any alias
	query= '''SELECT * FROM facilities 
					WHERE facility_name = ? 
					OR ',' || facility_aliases || ',' LIKE ?
	'''
	
	search_with_commas = f',{facility_name},'
	cursor.execute(query, (facility_name, f'%{search_with_commas}%'))

	result = cursor.fetchone()
	conn.close()

	if result:
		return {
			'id' : result[0],
			'facility_name': result[1],  # Name
			'facility_aliases': result[2], #Alias
			'facility_type': result[3],  # #Type
			'image_url': result[4]  # Image
		}
	return None


# Function to retrieve an item from the database (for testing)
def get_item_from_db(item_name):
	conn = connect_db()
	cursor = conn.cursor()
	
	query= '''SELECT * FROM items 
					WHERE item_name = ? 
					OR ',' || item_aliases || ',' LIKE ?
	'''
	
	search_with_commas = f',{item_name},'
	cursor.execute(query, (item_name, f'%{search_with_commas}%'))
	
	result = cursor.fetchone()
	conn.close()
	
	#Return query as dictionary
	if result:
		return {
			'id' : result[0],
			'item_name': result[1],
			'item_aliases': result[2],
			'facilities': result[3],
			'can_be_crated': result[4],
			'can_be_palleted': result[5],
			'crate_size': result[6],
			'pallet_size': result[7],
			'image_url': result[8],
		}
	return None
	
#Retrieve stockpile from database
def get_stockpile_from_db(stockpile_name):
	conn = connect_db()
	cursor = conn.cursor()
	
	query= '''SELECT * FROM stockpiles 
					WHERE stockpile_name = ? 
	'''
	
	cursor.execute(query, (stockpile_name,))

	result = cursor.fetchone()
	conn.close()

	if result:
		return {
			'id' : result[0],
			'stockpile_name': result[1],
			'stockpile_description': result[2],
			'stockpile_location': result[3],
			'stockpile_passcode': result[4]
		}
	return None
	
def create_task(item_id, amount, facility_id, stockpile_id, created_by, assigned_users, thumbnail):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (item_id, amount, current_amount, facility_id, stockpile_id, created_by, assigned_users, thumbnail, status)
        VALUES (?, ?, 0, ?, ?, ?, ?, ?, 'running')
    """, (item_id, amount, facility_id, stockpile_id, created_by, json.dumps(assigned_users), thumbnail))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def create_custom_task(task_header, task_description, task_location, created_by, assigned_users):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO custom_tasks (task_header, task_description, task_location, created_by, assigned_users)
            VALUES (?, ?, ?, ?, ?)
        """, (task_header, task_description, task_location, created_by, json.dumps(assigned_users)))
        task_id = cursor.lastrowid
        conn.commit()
        return task_id
    except Exception as e:
        print(f"Error creating custom task: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def save_task_message(task_id, message_id, channel_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("""
		UPDATE tasks
		SET message_id = ?, channel_id = ?
		WHERE id = ?
	""", (message_id, channel_id, task_id))
	conn.commit()
	conn.close()
	
def save_custom_task_message(task_id, message_id, channel_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("""
		UPDATE custom_tasks
		SET message_id = ?, channel_id = ?
		WHERE id = ?
	""", (message_id, channel_id, task_id))
	conn.commit()
	conn.close()


def add_user_to_task(task_id, user_id):
    conn = connect_db()
    cursor = conn.cursor()
    # Get the current assigned users from the task
    cursor.execute("SELECT assigned_users FROM tasks WHERE id = ?", (task_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        assigned_users = json.loads(result[0])
    else:
        assigned_users = []

    # Add the user to the list if not already there
    if str(user_id) not in assigned_users:
        assigned_users.append(str(user_id))

    # Update the task with the new list of assigned users
    cursor.execute(
        "UPDATE tasks SET assigned_users = ? WHERE id = ?",
        (json.dumps(assigned_users), task_id)
    )
    conn.commit()
    conn.close()

def add_user_to_custom_task(task_id, user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT assigned_users FROM custom_tasks WHERE id = ?", (task_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        assigned_users = json.loads(result[0])
    else:
        assigned_users = []

    if str(user_id) not in assigned_users:
        assigned_users.append(str(user_id))

    cursor.execute(
        "UPDATE custom_tasks SET assigned_users = ? WHERE id = ?",
        (json.dumps(assigned_users), task_id)
    )
    conn.commit()
    conn.close()

def close_task(task_id):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        logger.info(f"Task {task_id} deleted from the database")
    except Exception as e:
        logger.error(f"Error deleting task {task_id} from the database: {str(e)}")
        raise

def close_custom_task(task_id):
	try:
		conn = connect_db()
		cursor = conn.cursor()
		cursor.execute("DELETE FROM custom_tasks WHERE id = ?", (task_id,))
		conn.commit()
		conn.close()
		logger.info(f"Task {task_id} deleted from the database")
	except Exception as e:	
		logger.error(f"Error deleting task {task_id} from the database: {str(e)}")
		raise

def get_task(task_id):
	conn = connect_db()
	cursor = conn.cursor()
	
	query= '''SELECT * FROM tasks 
					WHERE id = ? 
	'''
	
	cursor.execute(query, (task_id,))

	result = cursor.fetchall()
	conn.close()

	if result:
		return {
			'id' : result[0],
		}
	return None

def get_custom_task(task_id):
	conn = connect_db()
	cursor = conn.cursor()
	
	query= '''SELECT * FROM custom_tasks 
					WHERE id = ? 
	'''	
	
	cursor.execute(query, (task_id,))

	result = cursor.fetchall()
	conn.close()

	if result:
		return {
			'id' : result[0],
		}	
	return None

def purge_tasks():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("DELETE FROM tasks")
	conn.commit()
	conn.close()
	
def purge_custom_tasks():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("DELETE FROM custom_tasks")
	conn.commit()
	conn.close()

def purge_stockpiles():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("DELETE FROM stockpiles")
	conn.commit()
	conn.close()

async def save_task_message(task_id, message_id, channel_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("""
		UPDATE tasks
		SET message_id = ?, channel_id = ?
		WHERE id = ?
	""", (message_id, channel_id, task_id))
	conn.commit()
	conn.close()
	
async def save_custom_task_message(task_id, message_id, channel_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE custom_tasks
        SET message_id = ?, channel_id = ?
        WHERE id = ?
    """, (message_id, channel_id, task_id))
    conn.commit()
    conn.close()

async def update_task_message_id(task_id, message_id):
	conn = connect_db()	
	cursor = conn.cursor()
	cursor.execute("UPDATE tasks SET message_id = ? WHERE id = ?", (message_id, task_id))
	conn.commit()

async def update_custom_task_message_id(task_id, message_id):
	conn = connect_db()	
	cursor = conn.cursor()
	cursor.execute("UPDATE custom_tasks SET message_id = ? WHERE id = ?", (message_id, task_id))
	conn.commit()
	conn.close()

async def get_task_message(task_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT message_id, channel_id FROM tasks WHERE task_id = ?", (task_id,))
	result = cursor.fetchone()
	if result:
		return {'message_id': result[0], 'channel_id': result[1]}
	return None

async def get_custom_task_message(task_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT message_id, channel_id FROM custom_tasks WHERE task_id = ?", (task_id,))
	result = cursor.fetchone()
	if result:
		return {'message_id': result[0], 'channel_id': result[1]}
	return None

def get_all_tasks():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT id, message_id, channel_id FROM tasks")
	tasks = cursor.fetchall()
	conn.close()
	return tasks

def get_all_custom_tasks():
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT id, message_id, channel_id FROM custom_tasks")
	tasks = cursor.fetchall()
	conn.close()
	return tasks

def get_task(task_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
	task = cursor.fetchone()
	conn.close()
	if task:
		return {
			'id': task[0],
			'message_id': task[1],
			'channel_id': task[2],
			'item_id': task[3],
			'amount': task[4],
			'current_amount': task[5],
			'facility_id': task[6],
			'stockpile_id': task[7],
			'created_by': task[8],
			'assigned_users': task[9],
			'thumbnail': task[10],
			'status': task[11]
		}
	return None

def get_custom_task(task_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM custom_tasks WHERE id = ?", (task_id,))
	task = cursor.fetchone()
	conn.close()
	if task:
		return {
			'id': task[0],
			'message_id': task[1],
			'channel_id': task[2],
			'task_header': task[3],
			'task_description': task[4],
			'task_location': task[5],
			'created_by': task[6],
			'assigned_users': task[7],
			'status': task[8]
		}
	return None

def update_task_message_id(task_id, message_id):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("UPDATE tasks SET message_id = ? WHERE id = ?", (message_id, task_id))
	conn.commit()
	conn.close()

def update_task_progress(task_id, new_amount):
	conn = connect_db()
	cursor = conn.cursor()
	cursor.execute("UPDATE tasks SET current_amount = ? WHERE id = ?", (new_amount, task_id))
	conn.commit()
	conn.close()
	logger.info(f"Updated task {task_id} progress to {new_amount}")

def get_task(task_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, i.item_name, f.facility_name, s.stockpile_name
        FROM tasks t
        JOIN items i ON t.item_id = i.id
        JOIN facilities f ON t.facility_id = f.id
        JOIN stockpiles s ON t.stockpile_id = s.id
        WHERE t.id = ?
    """, (task_id,))
    task = cursor.fetchone()
    conn.close()
    if task:
        task_dict = {
            'id': task[0],
            'message_id': task[1],
            'channel_id': task[2],
            'item_id': task[3],
            'amount': task[4],
            'current_amount': task[5],
            'facility_id': task[6],
            'stockpile_id': task[7],
            'created_by': task[8],
            'assigned_users': task[9],
            'thumbnail': task[10],
            'status': task[11],
            'item_name': task[12],
            'facility_name': task[13],
            'stockpile_name': task[14]
        }
        logger.info(f"Retrieved task: {task_dict}")
        return task_dict
    logger.warning(f"No task found with id {task_id}")
    return None

def check_database_health():
    try:
        conn = sqlite3.connect('main_data.db', timeout=10)
        cursor = conn.cursor()
        
        # Try to perform a simple query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Check if we can write to the database
        cursor.execute("CREATE TABLE IF NOT EXISTS health_check (id INTEGER PRIMARY KEY);")
        cursor.execute("INSERT INTO health_check (id) VALUES (1);")
        cursor.execute("DELETE FROM health_check WHERE id = 1;")
        
        conn.commit()
        conn.close()
        
        logger.info("Database health check passed. Database is accessible and writable.")
        return True
    except sqlite3.Error as e:
        if 'database is locked' in str(e):
            logger.error("Database health check failed: Database is locked. Please close any other connections and restart.")
        elif 'unable to open database file' in str(e):
            logger.error("Database health check failed: Unable to open database file. Check file permissions and path.")
        else:
            logger.error(f"Database health check failed: {str(e)}")
        return False

def update_task_assigned_users(task_id, assigned_users):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET assigned_users = ? WHERE id = ?",
        (assigned_users, task_id)
    )
    conn.commit()
    conn.close()

def update_custom_task_assigned_users(task_id, assigned_users):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE custom_tasks SET assigned_users = ? WHERE id = ?",
        (assigned_users, task_id)
    )	
    conn.commit()
    conn.close()
	
def update_task_status(task_id, status):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()

def update_item(item):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE items
            SET item_name = ?, item_aliases = ?, can_be_crated = ?, can_be_palleted = ?, 
                crate_size = ?, pallet_size = ?, facilities = ?, image_url = ?
            WHERE id = ?
        """, (item['item_name'], item['item_aliases'], item['can_be_crated'], item['can_be_palleted'],
              item['crate_size'], item['pallet_size'], item['facilities'], item['image_url'], item['id']))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating item: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()