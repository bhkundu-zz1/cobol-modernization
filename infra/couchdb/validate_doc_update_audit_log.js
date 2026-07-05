// validate_doc_update design function for the `audit_log` database.
//
// Status: [REAL]. Installed by infra/couchdb/init_databases.py onto the
// `audit_log` database's `_design/validate` design document (the source of
// truth for the deployed function is inlined there as a Python string,
// since CouchDB reads the function from the design doc, not this file
// directly — this file exists as the readable/reviewable canonical copy).
//
// Purpose (architecture.md section 6.2): CouchDB itself must reject any
// update or delete attempt on audit_event documents server-side, even from
// a caller with direct database credentials bypassing the MCP gateway's
// audit.append tool (which only ever supports create). This is
// defense-in-depth for the SEC 17a-4 "audit-trail alternative" design:
// hash-chain tamper-evidence plus enforced immutability at two independent
// layers (application: MCP tool has no update/delete method at all;
// database: this function).

function(newDoc, oldDoc, userCtx) {
  if (oldDoc && !newDoc._deleted) {
    throw({forbidden: "audit_log documents are append-only: updates are not permitted."});
  }
  if (newDoc._deleted) {
    throw({forbidden: "audit_log documents are append-only: deletes are not permitted."});
  }
}
