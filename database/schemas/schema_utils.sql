USE muistot;

DELIMITER $$

DROP PROCEDURE IF EXISTS analyze_all_tables $$
CREATE PROCEDURE analyze_all_tables()
BEGIN
    SET @table_list = NULL;
    SHOW TABLES WHERE (@table_list := CONCAT_WS(',', @table_list, `Tables_in_muistot`));
    SET @table_list := CONCAT('ANALYZE TABLE ', @table_list);
    PREPARE tasks FROM @table_list;
    EXECUTE tasks;
    DEALLOCATE PREPARE tasks;
    SET @table_list = NULL;
END $$

DROP EVENT IF EXISTS check_tables;
CREATE EVENT check_tables
    ON SCHEDULE EVERY 1 WEEK
        STARTS '2021-01-01 02:10:00'
    DO CALL analyze_all_tables() $$

DELIMITER ;

SET GLOBAL event_scheduler = TRUE;

CALL analyze_all_tables();