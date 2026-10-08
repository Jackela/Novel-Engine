import { mkdir, mkdtemp, copyFile, chmod, access, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";
import { buildAuthApp, setupOwner, loginOwner, cookieJar, cookieHeader } from "__BASELINE__/server/tests/api/auth_helpers.ts";
import { backupDatabaseFile } from "__BASELINE__/server/src/shared/infrastructure/db/backup.ts";
import { restoreDatabaseFile } from "__BASELINE__/server/src/shared/infrastructure/db/restore.ts";
import { openStudioDatabase } from "__BASELINE__/server/src/shared/infrastructure/db/startup.ts";
import { owners } from "__BASELINE__/server/src/shared/infrastructure/db/schema.ts";
const observations: Record<string,unknown>={baseline:"066d923d8bb92a47c7d6a12d8352b2aa471cbd4b"};
async function record(name:string,value:unknown){observations[name]=value;await writeFile("__BASELINE__-observations.json",JSON.stringify(observations,null,2));}
async function database(){const dir=await mkdtemp(join(tmpdir(),"ne-audit-database-"));const path=join(dir,"novel-engine.sqlite3");const studio=await openStudioDatabase(path);studio.db.insert(owners).values({id:"audit-owner",username:"before",password_hash:"synthetic-only",created_at:new Date("2026-10-01T00:00:00.000Z")}).run();studio.close();return {dir,path};}
describe("fixed-baseline acceptance reproductions",()=>{
 it("multibyte mismatched CSRF should return 403 rather than an internal error",async()=>{const {app}=await buildAuthApp();try{await setupOwner(app);const jar=cookieJar(await loginOwner(app));const token=jar.get("novel_engine_csrf")??"";const response=await app.inject({method:"DELETE",url:"/api/session",headers:{cookie:cookieHeader(jar),"x-csrf-token":"é".repeat(token.length)}});const still=await app.inject({method:"GET",url:"/api/session",headers:{cookie:cookieHeader(jar)}});await record("csrf_multibyte",{status:response.statusCode,error:response.json().error?.code,session_after_status:still.statusCode});expect(response.statusCode).toBe(403);expect(still.statusCode).toBe(200);}finally{await app.close();}});
 it("backup must report permission failure rather than no database",async()=>{const {dir,path}=await database();await chmod(dir,0o000);try{const result=await backupDatabaseFile(path);await record("backup_permission",{result});expect(result).not.toBeNull();}finally{await chmod(dir,0o700);}});
 it("restore input must survive safety backup retention",async()=>{const {dir,path}=await database();const backups=join(dir,"backups");await mkdir(backups);const names=["novel-engine-20200101T000000000Z.sqlite3.bak","novel-engine-20200102T000000000Z.sqlite3.bak","novel-engine-20200103T000000000Z.sqlite3.bak"];for(const name of names)await copyFile(path,join(backups,name));const input=join(backups,names[0]);const current=new Database(path);current.prepare("UPDATE owners SET username=?").run("after");current.close();let failure:unknown;try{await restoreDatabaseFile(path,input);}catch(error){failure=error;}let inputExists=true;try{await access(input);}catch{inputExists=false;}const read=new Database(path,{readonly:true,fileMustExist:true});const owner=read.prepare("SELECT username FROM owners").get();read.close();await record("restore_retention",{failure:failure instanceof Error?failure.message:String(failure),input_exists:inputExists,owner});expect(failure).toBeUndefined();expect(inputExists).toBe(true);});
});
