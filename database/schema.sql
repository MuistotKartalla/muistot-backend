CREATE TABLE call_log
(
    id      BIGINT UNSIGNED                                                                       NOT NULL AUTO_INCREMENT,
    time    TIMESTAMP                                                                             NOT NULL DEFAULT CURRENT_TIMESTAMP,
    method  ENUM ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH') NOT NULL DEFAULT 'GET',
    target  VARCHAR(256)                                                                          NOT NULL DEFAULT '/',
    payload BLOB                                                                                  NULL     DEFAULT NULL,
    headers BLOB                                                                                  NULL     DEFAULT NULL,
    PRIMARY KEY pk_call_log (id),
    INDEX idx_time (time, method),
    INDEX idx_time (time, target)
) ENGINE = MyISAM COMMENT 'This can be left out of production';

CREATE TABLE images
(
    id        INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
    file_name CHAR(32)         NOT NULL COMMENT 'THIS IS UUID OR GENERATED NEVER INPUT' COLLATE ascii_general_ci,
    PRIMARY KEY pk_images (id)
) COMMENT 'Unified storage for image files';

CREATE TABLE projects
(
    id      INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
    logo_id INTEGER UNSIGNED NULL DEFAULT NULL,
    starts  DATE             NULL DEFAULT NULL,
    ends    DATE             NULL DEFAULT NULL,
    deleted BOOLEAN               DEFAULT FALSE,
    PRIMARY KEY pk_projects (id),
    INDEX idx_dates (starts, ends),
    INDEX idx_deleted (deleted),
    CONSTRAINT FOREIGN KEY fk_project_logo (logo_id) REFERENCES images (id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE TABLE languages
(
    lang VARCHAR(10) NOT NULL,
    PRIMARY KEY pk_languages (lang)
);

CREATE TABLE project_information
(
    id          INTEGER UNSIGNED NOT NULL,
    lang        VARCHAR(10),
    name        VARCHAR(256),
    abstract    TEXT,
    description LONGTEXT,
    CONSTRAINT FOREIGN KEY fg_pi_id (id) REFERENCES projects (id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fg_pi_lang (lang) REFERENCES languages (lang)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) COMMENT 'Lang is restricted since it is in use';

