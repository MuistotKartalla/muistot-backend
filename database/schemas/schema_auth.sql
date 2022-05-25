/*
    This is supposed to be used to implement various auth methods
 */
USE muistot;

CREATE TABLE IF NOT EXISTS auth_providers
(
    id   INTEGER     NOT NULL AUTO_INCREMENT,
    name VARCHAR(15) NOT NULL,

    PRIMARY KEY pk_oap (id),
    UNIQUE INDEX idx_oap_name (name)
) COMMENT 'Stores OAuth providers';

INSERT IGNORE INTO auth_providers (name)
VALUES ('google'),
       ('facebook'),
       ('twitter')
;

CREATE TABLE IF NOT EXISTS auth_provider_data
(
    service_id INTEGER NOT NULL COMMENT 'fk',
    data       BLOB    NULL COMMENT 'Stores serialized OAuth data for this service',

    PRIMARY KEY pk_apd (service_id),
    CONSTRAINT FOREIGN KEY fk_apd_service (service_id) REFERENCES auth_providers (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Links users to OAuth providers';

CREATE TABLE IF NOT EXISTS auth_provider_user_data
(
    user_id    INTEGER NOT NULL COMMENT 'fk',
    service_id INTEGER NOT NULL COMMENT 'fk',
    data       BLOB    NULL COMMENT 'Stores serialized OAuth data for this user for this service',

    PRIMARY KEY pk_apud (user_id, service_id),
    CONSTRAINT FOREIGN KEY fk_apud_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_apud_service (service_id) REFERENCES auth_providers (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Links users to OAuth providers';

