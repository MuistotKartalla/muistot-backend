# Adds system versioning to chosen subset of tables for easy recovery
# - Sites are modifiable by users on some projects.
# - Audit log should be kept of who was an admin and when
# - Memories and Comments will not be versioned as they should be deleted
ALTER TABLE sites
    ADD SYSTEM VERSIONING;
ALTER TABLE site_information
    ADD SYSTEM VERSIONING;
ALTER TABLE projects
    ADD SYSTEM VERSIONING;
ALTER TABLE project_information
    ADD SYSTEM VERSIONING;
ALTER TABLE project_contact
    ADD SYSTEM VERSIONING;
ALTER TABLE project_admins
    ADD SYSTEM VERSIONING;
ALTER TABLE superusers
    ADD SYSTEM VERSIONING;