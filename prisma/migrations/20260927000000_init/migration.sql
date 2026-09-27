-- CreateEnum
CREATE TYPE "user_role" AS ENUM ('admin_secretary', 'signer', 'public_verifier');

-- CreateEnum
CREATE TYPE "document_status" AS ENUM ('DRAFT', 'UPLOADED', 'READY', 'SIGNING', 'SIGNED', 'INVALID', 'REVOKED');

-- CreateEnum
CREATE TYPE "signing_request_status" AS ENUM ('PENDING', 'SIGNED', 'EXPIRED', 'CANCELLED');

-- CreateTable
CREATE TABLE "profiles" (
    "id" UUID NOT NULL,
    "full_name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "role" "user_role" NOT NULL DEFAULT 'signer',
    "position" TEXT,
    "institution" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "profiles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "documents" (
    "id" UUID NOT NULL,
    "owner_id" UUID NOT NULL,
    "original_filename" TEXT NOT NULL,
    "mime_type" TEXT NOT NULL,
    "file_size" BIGINT NOT NULL,
    "source_sha256" CHAR(64) NOT NULL,
    "storage_original_path" TEXT NOT NULL,
    "storage_signed_path" TEXT,
    "status" "document_status" NOT NULL DEFAULT 'DRAFT',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "documents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "signing_keys" (
    "id" UUID NOT NULL,
    "owner_id" UUID NOT NULL,
    "algorithm" TEXT NOT NULL DEFAULT 'RSA',
    "key_size" INTEGER NOT NULL DEFAULT 2048,
    "public_key_pem" TEXT NOT NULL,
    "public_key_fingerprint" CHAR(64) NOT NULL,
    "encrypted_private_key" BYTEA NOT NULL,
    "encryption_algorithm" TEXT NOT NULL DEFAULT 'AES-256-GCM',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "rotated_at" TIMESTAMP(3),

    CONSTRAINT "signing_keys_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "signing_requests" (
    "id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "signer_id" UUID NOT NULL,
    "status" "signing_request_status" NOT NULL DEFAULT 'PENDING',
    "requested_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "signed_at" TIMESTAMP(3),
    "expires_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "signing_requests_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "signature_positions" (
    "id" UUID NOT NULL,
    "signing_request_id" UUID NOT NULL,
    "page_number" INTEGER NOT NULL,
    "x" DECIMAL(65,30) NOT NULL,
    "y" DECIMAL(65,30) NOT NULL,
    "width" DECIMAL(65,30) NOT NULL,
    "height" DECIMAL(65,30) NOT NULL,

    CONSTRAINT "signature_positions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "signatures" (
    "id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "signer_id" UUID NOT NULL,
    "signing_key_id" UUID NOT NULL,
    "algorithm" TEXT NOT NULL DEFAULT 'RSA-PSS',
    "hash_algorithm" TEXT NOT NULL DEFAULT 'SHA-256',
    "key_algorithm" TEXT NOT NULL DEFAULT 'RSA-2048',
    "public_key_fingerprint" CHAR(64) NOT NULL,
    "signature_fingerprint" CHAR(64) NOT NULL,
    "signed_pdf_sha256" CHAR(64) NOT NULL,
    "signed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "verification_token_hash" CHAR(64) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "signatures_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "verification_records" (
    "id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "signature_id" UUID NOT NULL,
    "token_hash" CHAR(64) NOT NULL,
    "public_status" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "verification_records_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_logs" (
    "id" BIGSERIAL NOT NULL,
    "actor_id" UUID,
    "event_type" TEXT NOT NULL,
    "document_id" UUID,
    "signature_id" UUID,
    "ip_hash" CHAR(64),
    "user_agent" TEXT,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "previous_event_hash" CHAR(64),
    "event_hash" CHAR(64) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "profiles_email_key" ON "profiles"("email");

-- CreateIndex
CREATE INDEX "documents_owner_id_idx" ON "documents"("owner_id");

-- CreateIndex
CREATE INDEX "signing_requests_document_id_idx" ON "signing_requests"("document_id");

-- CreateIndex
CREATE UNIQUE INDEX "signatures_verification_token_hash_key" ON "signatures"("verification_token_hash");

-- CreateIndex
CREATE INDEX "signatures_document_id_idx" ON "signatures"("document_id");

-- CreateIndex
CREATE UNIQUE INDEX "verification_records_token_hash_key" ON "verification_records"("token_hash");

-- CreateIndex
CREATE INDEX "audit_logs_document_id_idx" ON "audit_logs"("document_id");

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signing_keys" ADD CONSTRAINT "signing_keys_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signing_requests" ADD CONSTRAINT "signing_requests_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signing_requests" ADD CONSTRAINT "signing_requests_signer_id_fkey" FOREIGN KEY ("signer_id") REFERENCES "profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signature_positions" ADD CONSTRAINT "signature_positions_signing_request_id_fkey" FOREIGN KEY ("signing_request_id") REFERENCES "signing_requests"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signatures" ADD CONSTRAINT "signatures_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signatures" ADD CONSTRAINT "signatures_signer_id_fkey" FOREIGN KEY ("signer_id") REFERENCES "profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "signatures" ADD CONSTRAINT "signatures_signing_key_id_fkey" FOREIGN KEY ("signing_key_id") REFERENCES "signing_keys"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "verification_records" ADD CONSTRAINT "verification_records_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "verification_records" ADD CONSTRAINT "verification_records_signature_id_fkey" FOREIGN KEY ("signature_id") REFERENCES "signatures"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "profiles"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE SET NULL ON UPDATE CASCADE;


-- Partial unique index (manual, per PRD §6)
create unique index idx_signing_keys_owner_active on signing_keys(owner_id) where rotated_at is null;
