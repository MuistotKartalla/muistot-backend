ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS default_language_id INTEGER NOT NULL;
UPDATE projects
SET default_language_id = (SELECT id FROM languages WHERE lang = 'fi')
WHERE default_language_id = 0;
ALTER TABLE projects
    ADD CONSTRAINT FOREIGN KEY IF NOT EXISTS fk_projects_default_language (default_language_id) REFERENCES languages (id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT;
