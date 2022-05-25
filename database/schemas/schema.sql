CREATE DATABASE IF NOT EXISTS muistot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE muistot;

/*
    Languages used in the application
*/

CREATE TABLE IF NOT EXISTS languages
(
    id   INTEGER    NOT NULL AUTO_INCREMENT,
    lang VARCHAR(5) NOT NULL,

    PRIMARY KEY pk_languages (id),
    UNIQUE INDEX idx_lang (lang)
) COMMENT 'Stores localization languages';

INSERT IGNORE INTO languages (lang)
VALUES ('fi'),
       ('en');

/*
    Create User Tables
*/

CREATE TABLE IF NOT EXISTS users
(
    id            INTEGER      NOT NULL AUTO_INCREMENT,
    email         VARCHAR(255) NULL     DEFAULT NULL,
    username      VARCHAR(255) NOT NULL,
    password_hash BINARY(60) COMMENT 'BCrypt',

    # important
    verified      BOOLEAN               DEFAULT FALSE,
    modified_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at    DATETIME              DEFAULT CURRENT_TIMESTAMP,

    # basic data
    image_id      INTEGER      NULL COMMENT 'fk',
    lang_id       INTEGER      NULL COMMENT 'fk',

    PRIMARY KEY pk_users (id),
    UNIQUE INDEX idx_users_username (username),
    UNIQUE INDEX idx_users_email (email),

    CONSTRAINT FOREIGN KEY fk_users_language (lang_id) REFERENCES languages (id)
) COMMENT 'Stores user data';

CREATE TABLE IF NOT EXISTS images
(
    id          INTEGER      NOT NULL AUTO_INCREMENT,
    created_at  DATETIME     NOT NULL                                                     DEFAULT CURRENT_TIMESTAMP,
    uploader_id INTEGER      NULL COMMENT 'fk',
    file_name   VARCHAR(100) NOT NULL COMMENT 'Never From Input' COLLATE ascii_general_ci DEFAULT UUID(),

    PRIMARY KEY pk_images (id),
    INDEX idx_images_uploader (uploader_id),
    CONSTRAINT FOREIGN KEY fk_images_uploader (uploader_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Unified storage for image files';

ALTER TABLE users
    ADD CONSTRAINT FOREIGN KEY IF NOT EXISTS fk_users_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS user_email_verifiers
(
    user_id    INTEGER      NOT NULL,
    verifier   VARCHAR(255) NOT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY pk_uev (user_id),
    INDEX idx_uev_date (created_at),

    CONSTRAINT FOREIGN KEY fk_uc_user_id (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Stores user verifier data';

CREATE TABLE IF NOT EXISTS user_personal_data
(
    user_id     INTEGER      NOT NULL,
    first_name  VARCHAR(255) NULL,
    last_name   VARCHAR(255) NULL,
    birth_date  DATE         NULL DEFAULT NULL,
    country     VARCHAR(5)   NULL,
    city        VARCHAR(255) NULL,

    modified_at DATETIME          DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_upd (user_id),
    INDEX idx_upd_name (last_name, first_name),
    INDEX idx_upd_location (country, city),
    INDEX idx_upd_birthdate (birth_date),

    CONSTRAINT FOREIGN KEY fk_upd_user_id (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'User personal data';

CREATE TABLE IF NOT EXISTS superusers
(
    user_id    INTEGER  NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY pk_superusers (user_id),

    CONSTRAINT FOREIGN KEY fk_superusers (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Global SuperUsers';
