USE muistot;

DROP TABLE IF EXISTS audit_memories;
CREATE TABLE IF NOT EXISTS audit_memories
(
    memory_id INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,

    PRIMARY KEY pk_am (memory_id, user_id),
    CONSTRAINT FOREIGN KEY fg_am_memory (memory_id) REFERENCES memories (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fg_am_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);

DROP TABLE IF EXISTS audit_sites;
CREATE TABLE IF NOT EXISTS audit_sites
(
    site_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,

    PRIMARY KEY pk_as (site_id, user_id),
    CONSTRAINT FOREIGN KEY fg_as_site (site_id) REFERENCES sites (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fg_as_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);

DELIMITER $$

DROP PROCEDURE IF EXISTS hide_reported_things;
CREATE PROCEDURE hide_reported_things()
BEGIN
    # Memories
    UPDATE memories m
        JOIN (
            SELECT memory_id,
                   COUNT(*) AS report_count
            FROM audit_memories
            GROUP BY memory_id
        ) audit ON audit.memory_id = m.id
    SET m.published = 0
    WHERE audit.report_count > 10;
    # Sites
    UPDATE sites s
        JOIN (
            SELECT site_id,
                   COUNT(*) AS report_count
            FROM audit_sites
            GROUP BY site_id
        ) audit ON audit.site_id = s.id
    SET s.published = 0
    WHERE audit.report_count > 10;
    # End
END $$

CREATE EVENT IF NOT EXISTS report_watchdog
    ON SCHEDULE EVERY 12 HOUR
        STARTS '2021-01-01 00:00:00'
    DO CALL hide_reported_things() $$

DELIMITER ;