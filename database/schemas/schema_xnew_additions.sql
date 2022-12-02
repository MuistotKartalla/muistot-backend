USE muistot;

CREATE TABLE IF NOT EXISTS login_log
(
    user_id     INTEGER      NULL,

    username    VARCHAR(255) NOT NULL,
    superuser   BOOLEAN      NOT NULL DEFAULT FALSE,
    admin_in    TEXT,
    `timestamp` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_login_log_time (timestamp),

    CONSTRAINT FOREIGN KEY fk_login_log_track (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL

) ROW_FORMAT = DYNAMIC, COMMENT = 'Login audit log';

DELIMITER $$

DROP PROCEDURE IF EXISTS log_login $$
CREATE PROCEDURE log_login(IN user VARCHAR(255))
BEGIN
    INSERT INTO login_log (user_id, username, superuser, admin_in)
    SELECT u.id,
           u.username,
           EXISTS(SELECT 1 FROM superusers su WHERE su.user_id = u.id),
           GROUP_CONCAT(p.name SEPARATOR ',')
    FROM users u
             LEFT JOIN project_admins pa ON u.id = pa.user_id
             JOIN projects p ON p.id = pa.project_id
    WHERE u.username = user
    GROUP BY u.id;
END $$

DELIMITER ;