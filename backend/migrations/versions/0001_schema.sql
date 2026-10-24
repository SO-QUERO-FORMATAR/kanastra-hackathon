
CREATE TABLE funds (
	id UUID NOT NULL, 
	cnpj TEXT NOT NULL, 
	name TEXT NOT NULL, 
	active_rule UUID, 
	PRIMARY KEY (id), 
	CHECK (cnpj ~ '^[0-9]{14}$'), 
	UNIQUE (cnpj)
)

;

CREATE TABLE idempotency (
	scope TEXT NOT NULL, 
	key UUID NOT NULL, 
	fingerprint TEXT NOT NULL, 
	status_code INTEGER NOT NULL, 
	response JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (scope, key)
)

;

CREATE TABLE registry_loads (
	id UUID NOT NULL, 
	sha256 TEXT NOT NULL, 
	count INTEGER NOT NULL, 
	active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (sha256)
)

;

CREATE TABLE exposures (
	fund_id UUID NOT NULL, 
	side TEXT NOT NULL, 
	root TEXT NOT NULL, 
	amount NUMERIC(38, 2) NOT NULL, 
	PRIMARY KEY (fund_id, side, root), 
	CHECK (side IN ('SACADO','CEDENTE')), 
	CHECK (root ~ '^[0-9]{8}$'), 
	FOREIGN KEY(fund_id) REFERENCES funds (id)
)

;

CREATE TABLE lots (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	status TEXT DEFAULT 'RECEBENDO' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	load_id UUID, 
	indexed BOOLEAN DEFAULT 'false' NOT NULL, 
	lines_read INTEGER DEFAULT '0' NOT NULL, 
	total_lines INTEGER, 
	processed INTEGER DEFAULT '0' NOT NULL, 
	error JSONB, 
	pending_revision INTEGER DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(load_id) REFERENCES registry_loads (id)
)

;

CREATE TABLE registry (
	load_id UUID NOT NULL, 
	document TEXT NOT NULL, 
	situation TEXT NOT NULL, 
	PRIMARY KEY (load_id, document), 
	CHECK (document ~ '^[0-9]{14}$'), 
	FOREIGN KEY(load_id) REFERENCES registry_loads (id)
)

;

CREATE TABLE rules (
	id UUID NOT NULL, 
	fund_id UUID NOT NULL, 
	configuration JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(fund_id) REFERENCES funds (id)
)

;

CREATE TABLE contexts (
	lot_id UUID NOT NULL, 
	fund_id UUID NOT NULL, 
	pl NUMERIC(38, 2) NOT NULL, 
	rule_id UUID, 
	PRIMARY KEY (lot_id, fund_id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(fund_id) REFERENCES funds (id), 
	FOREIGN KEY(rule_id) REFERENCES rules (id)
)

;

CREATE TABLE executions (
	id UUID NOT NULL, 
	lot_id UUID NOT NULL, 
	status TEXT DEFAULT 'QUEUED' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	heartbeat TIMESTAMP WITH TIME ZONE, 
	owner UUID, 
	checkpoint BIGINT DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id)
)

;

CREATE TABLE files (
	id UUID NOT NULL, 
	lot_id UUID NOT NULL, 
	client_id UUID NOT NULL, 
	position INTEGER NOT NULL, 
	name TEXT NOT NULL, 
	format TEXT NOT NULL, 
	sheet TEXT, 
	size BIGINT NOT NULL, 
	sha256 TEXT NOT NULL, 
	path TEXT, 
	status TEXT DEFAULT 'AGUARDANDO_UPLOAD' NOT NULL, 
	received_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	total_lines INTEGER, 
	processed INTEGER DEFAULT '0' NOT NULL, 
	error JSONB, 
	PRIMARY KEY (id), 
	UNIQUE (lot_id, client_id), 
	UNIQUE (lot_id, position), 
	UNIQUE (id, lot_id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id)
)

;

CREATE TABLE pending (
	id UUID NOT NULL, 
	lot_id UUID NOT NULL, 
	code TEXT NOT NULL, 
	fund_id UUID, 
	file_id UUID, 
	line INTEGER, 
	field TEXT, 
	message TEXT NOT NULL, 
	action TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(fund_id) REFERENCES funds (id), 
	FOREIGN KEY(file_id) REFERENCES files (id)
)

;

CREATE TABLE results (
	id UUID NOT NULL, 
	lot_id UUID NOT NULL, 
	file_id UUID NOT NULL, 
	sequence INTEGER NOT NULL, 
	line INTEGER NOT NULL, 
	fund_id UUID, 
	type TEXT NOT NULL, 
	status TEXT, 
	nominal NUMERIC(38, 2) DEFAULT '0' NOT NULL, 
	discount NUMERIC(38, 2) DEFAULT '0' NOT NULL, 
	net NUMERIC(38, 2) DEFAULT '0' NOT NULL, 
	payload JSONB NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (file_id, line), 
	UNIQUE (file_id, sequence), 
	CHECK ((type = 'ERRO_DADOS' AND status IS NULL) OR (type = 'ANALISE' AND status IN ('APROVADO','BARRADO'))), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(file_id) REFERENCES files (id), 
	FOREIGN KEY(fund_id) REFERENCES funds (id)
)

;

CREATE TABLE staging (
	file_id UUID NOT NULL, 
	line INTEGER NOT NULL, 
	sequence INTEGER NOT NULL, 
	fund_id UUID, 
	nominal NUMERIC(38, 2), 
	payload JSONB NOT NULL, 
	errors JSONB NOT NULL, 
	blocks_pl BOOLEAN DEFAULT 'false' NOT NULL, 
	PRIMARY KEY (file_id, line), 
	FOREIGN KEY(file_id) REFERENCES files (id), 
	FOREIGN KEY(fund_id) REFERENCES funds (id)
)

;

CREATE TABLE approved (
	seller TEXT NOT NULL, 
	debtor TEXT NOT NULL, 
	number TEXT NOT NULL, 
	fund_id UUID NOT NULL, 
	result_id UUID NOT NULL, 
	PRIMARY KEY (seller, debtor, number), 
	FOREIGN KEY(fund_id) REFERENCES funds (id), 
	UNIQUE (result_id), 
	FOREIGN KEY(result_id) REFERENCES results (id)
)

;

CREATE TABLE reasons (
	result_id UUID NOT NULL, 
	code TEXT NOT NULL, 
	PRIMARY KEY (result_id, code), 
	FOREIGN KEY(result_id) REFERENCES results (id)
)

;
CREATE UNIQUE INDEX one_active_registry ON registry_loads (active) WHERE active IS true;
CREATE INDEX lots_history ON lots (created_at DESC, id DESC);
CREATE INDEX results_type ON results (file_id, type, sequence);
CREATE INDEX results_filter ON results (file_id, status, sequence);
CREATE INDEX reasons_code ON reasons (code, result_id);
