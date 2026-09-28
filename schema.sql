-- LM订单管理系统 表结构（PostgreSQL）
-- 由 SQLAlchemy models.py 自动生成


CREATE TABLE category (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	parent_id INTEGER, 
	level SMALLINT NOT NULL, 
	sort_no SMALLINT, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES category (id)
)

;


CREATE TABLE channel (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE customer (
	id SERIAL NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	ctype VARCHAR(20) NOT NULL, 
	tg_id VARCHAR(100), 
	wash_mode VARCHAR(20), 
	is_accounted BOOLEAN, 
	discount NUMERIC(5, 4), 
	balance NUMERIC(14, 2), 
	warn_amount NUMERIC(14, 2), 
	start_date DATE, 
	end_date DATE, 
	note TEXT, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE daily_data (
	id SERIAL NOT NULL, 
	biz_date DATE NOT NULL, 
	upstream VARCHAR(100), 
	task_id VARCHAR(100), 
	task_name VARCHAR(200), 
	phone VARCHAR(20) NOT NULL, 
	name VARCHAR(50), 
	province VARCHAR(50), 
	city VARCHAR(50), 
	operator VARCHAR(50), 
	cat1 VARCHAR(100), 
	cat2 VARCHAR(100), 
	platform VARCHAR(100), 
	customer VARCHAR(100), 
	secondary_agent VARCHAR(100), 
	channel VARCHAR(100), 
	source_file VARCHAR(500), 
	source_file_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE fund (
	id SERIAL NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	name VARCHAR(50), 
	id_card VARCHAR(30), 
	gender VARCHAR(10), 
	province VARCHAR(50), 
	city VARCHAR(50), 
	company VARCHAR(200), 
	company_type VARCHAR(50), 
	base NUMERIC(14, 2), 
	ratio VARCHAR(20), 
	monthly NUMERIC(14, 2), 
	balance NUMERIC(14, 2), 
	deposit_status VARCHAR(20), 
	open_date VARCHAR(20), 
	pay_to VARCHAR(20), 
	operator VARCHAR(20), 
	source_file VARCHAR(200), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE operation_log (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	username VARCHAR(50), 
	module VARCHAR(50), 
	action VARCHAR(50), 
	target VARCHAR(200), 
	detail TEXT, 
	ip VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE operator (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE order_template (
	id SERIAL NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	party VARCHAR(20), 
	columns_json TEXT, 
	style_json TEXT, 
	filename_rule VARCHAR(200), 
	match_rule_json TEXT, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE source_file (
	id SERIAL NOT NULL, 
	filename VARCHAR(500), 
	file_data BYTEA, 
	file_type VARCHAR(20), 
	biz_date VARCHAR(50), 
	party VARCHAR(50), 
	size INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE sys_config (
	key VARCHAR(50) NOT NULL, 
	value VARCHAR(200), 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (key)
)

;


CREATE TABLE sys_permission (
	id SERIAL NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	label VARCHAR(100) NOT NULL, 
	module VARCHAR(50), 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE sys_role (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	is_builtin BOOLEAN, 
	note TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE template (
	id SERIAL NOT NULL, 
	ttype VARCHAR(50), 
	code VARCHAR(100) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	file_data BYTEA, 
	file_type VARCHAR(50), 
	description TEXT, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE tidabiao_history (
	id SERIAL NOT NULL, 
	batch_no VARCHAR(50), 
	order_id INTEGER, 
	order_no VARCHAR(50), 
	status VARCHAR(20), 
	order_date VARCHAR(50), 
	upstream VARCHAR(100), 
	customer VARCHAR(100), 
	secondary_agent VARCHAR(100), 
	channel VARCHAR(100), 
	operator VARCHAR(50), 
	task_name VARCHAR(200), 
	task_id VARCHAR(100), 
	url TEXT, 
	qty VARCHAR(50), 
	duration VARCHAR(50), 
	age_min VARCHAR(50), 
	age_max VARCHAR(50), 
	pv VARCHAR(50), 
	province VARCHAR(500), 
	city VARCHAR(500), 
	excl_province VARCHAR(500), 
	excl_city VARCHAR(500), 
	start_date VARCHAR(50), 
	end_date VARCHAR(50), 
	price VARCHAR(50), 
	platform VARCHAR(100), 
	group_name VARCHAR(100), 
	tpl_code VARCHAR(100), 
	add_name VARCHAR(10), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE wash_name (
	id SERIAL NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	name VARCHAR(50), 
	province VARCHAR(50), 
	city VARCHAR(50), 
	operator VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (phone)
)

;


CREATE TABLE alert (
	id SERIAL NOT NULL, 
	level VARCHAR(10) NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	customer_id INTEGER, 
	task_name VARCHAR(200), 
	content TEXT, 
	trigger_time TIMESTAMP WITHOUT TIME ZONE, 
	status VARCHAR(20), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id)
)

;


CREATE TABLE bill (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	biz_date DATE NOT NULL, 
	purchase_qty INTEGER, 
	sales NUMERIC(14, 2), 
	balance NUMERIC(14, 2), 
	profit NUMERIC(14, 2), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id)
)

;


CREATE TABLE customer_price (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	channel_id INTEGER NOT NULL, 
	price NUMERIC(8, 4) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id), 
	FOREIGN KEY(channel_id) REFERENCES channel (id)
)

;


CREATE TABLE customer_recharge (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	recharge_date DATE NOT NULL, 
	amount_u NUMERIC(14, 2) NOT NULL, 
	amount_rmb NUMERIC(14, 2), 
	note TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id)
)

;


CREATE TABLE orders (
	id SERIAL NOT NULL, 
	order_no VARCHAR(50) NOT NULL, 
	customer_id INTEGER, 
	upstream_id INTEGER, 
	channel_id INTEGER, 
	operator_id INTEGER, 
	task_name VARCHAR(200), 
	task_id VARCHAR(100), 
	qty INTEGER, 
	duration VARCHAR(50), 
	province VARCHAR(500), 
	city VARCHAR(500), 
	excl_province VARCHAR(500), 
	excl_city VARCHAR(500), 
	age_min INTEGER, 
	age_max INTEGER, 
	pv INTEGER, 
	start_date DATE, 
	end_date DATE, 
	stop_date DATE, 
	status VARCHAR(20), 
	batch_no VARCHAR(50), 
	dup_order_nos TEXT, 
	change_fields_json TEXT, 
	template_id INTEGER, 
	filename_rule VARCHAR(200), 
	dist_config_json TEXT, 
	order_date DATE, 
	price NUMERIC(10, 4), 
	secondary_agent VARCHAR(100), 
	platform VARCHAR(100), 
	tpl_id INTEGER, 
	group_name VARCHAR(100), 
	export_filename VARCHAR(200), 
	add_name BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (order_no), 
	FOREIGN KEY(customer_id) REFERENCES customer (id), 
	FOREIGN KEY(upstream_id) REFERENCES customer (id), 
	FOREIGN KEY(channel_id) REFERENCES channel (id), 
	FOREIGN KEY(operator_id) REFERENCES operator (id), 
	FOREIGN KEY(template_id) REFERENCES order_template (id), 
	FOREIGN KEY(tpl_id) REFERENCES template (id)
)

;


CREATE TABLE platform (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	cat_id INTEGER NOT NULL, 
	sort_no SMALLINT, 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(cat_id) REFERENCES category (id)
)

;


CREATE TABLE sys_role_permission (
	role_id INTEGER NOT NULL, 
	permission_id INTEGER NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES sys_role (id), 
	FOREIGN KEY(permission_id) REFERENCES sys_permission (id)
)

;


CREATE TABLE sys_user (
	id SERIAL NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	password_hash VARCHAR(200) NOT NULL, 
	nickname VARCHAR(50), 
	role_id INTEGER, 
	status SMALLINT, 
	must_change_pwd BOOLEAN, 
	last_login_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	FOREIGN KEY(role_id) REFERENCES sys_role (id)
)

;


CREATE TABLE ai_session (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	title VARCHAR(100), 
	archived BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES sys_user (id)
)

;


CREATE TABLE order_url (
	id SERIAL NOT NULL, 
	order_id INTEGER NOT NULL, 
	url TEXT NOT NULL, 
	level VARCHAR(10), 
	sort_no SMALLINT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
)

;


CREATE TABLE url (
	id SERIAL NOT NULL, 
	name VARCHAR(200), 
	owner_id INTEGER, 
	cat1_id INTEGER, 
	cat2_id INTEGER, 
	platform_id INTEGER, 
	channel_id INTEGER, 
	url TEXT NOT NULL, 
	level VARCHAR(10), 
	status SMALLINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES customer (id), 
	FOREIGN KEY(cat1_id) REFERENCES category (id), 
	FOREIGN KEY(cat2_id) REFERENCES category (id), 
	FOREIGN KEY(platform_id) REFERENCES platform (id), 
	FOREIGN KEY(channel_id) REFERENCES channel (id)
)

;


CREATE TABLE ai_message (
	id SERIAL NOT NULL, 
	session_id INTEGER NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content TEXT, 
	tool_calls_json TEXT, 
	model VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES ai_session (id)
)

;


CREATE TABLE ai_tool_call (
	id SERIAL NOT NULL, 
	session_id INTEGER, 
	message_id INTEGER, 
	user_id INTEGER, 
	tool VARCHAR(50) NOT NULL, 
	args_json TEXT, 
	risk VARCHAR(10), 
	status VARCHAR(20), 
	result_json TEXT, 
	error TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES ai_session (id), 
	FOREIGN KEY(message_id) REFERENCES ai_message (id)
)

;
