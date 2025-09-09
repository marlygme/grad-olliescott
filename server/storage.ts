import {
  users,
  applications,
  submissions,
  type User,
  type UpsertUser,
  type Application,
  type InsertApplication,
  type Submission,
  type InsertSubmission,
} from "../shared/schema";
import { db } from "./db";
import { eq, desc } from "drizzle-orm";

// Interface for storage operations
export interface IStorage {
  // User operations
  // (IMPORTANT) these user operations are mandatory for Replit Auth.
  getUser(id: string): Promise<User | undefined>;
  upsertUser(user: UpsertUser): Promise<User>;
  
  // Application operations
  getUserApplications(userId: string): Promise<Application[]>;
  createApplication(application: InsertApplication): Promise<Application>;
  updateApplication(id: number, application: Partial<InsertApplication>): Promise<Application>;
  deleteApplication(id: number, userId: string): Promise<boolean>;
  
  // Submission operations
  getUserSubmissions(userId: string): Promise<Submission[]>;
  getAllSubmissions(): Promise<Submission[]>;
  createSubmission(submission: InsertSubmission): Promise<Submission>;
}

export class DatabaseStorage implements IStorage {
  // User operations
  // (IMPORTANT) these user operations are mandatory for Replit Auth.

  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async upsertUser(userData: UpsertUser): Promise<User> {
    const [user] = await db
      .insert(users)
      .values(userData)
      .onConflictDoUpdate({
        target: users.id,
        set: {
          ...userData,
          updatedAt: new Date(),
        },
      })
      .returning();
    return user;
  }

  // Application operations
  async getUserApplications(userId: string): Promise<Application[]> {
    return await db
      .select()
      .from(applications)
      .where(eq(applications.userId, userId))
      .orderBy(desc(applications.createdAt));
  }

  async createApplication(application: InsertApplication): Promise<Application> {
    const [newApplication] = await db
      .insert(applications)
      .values(application)
      .returning();
    return newApplication;
  }

  async updateApplication(id: number, application: Partial<InsertApplication>): Promise<Application> {
    const [updatedApplication] = await db
      .update(applications)
      .set({ ...application, updatedAt: new Date() })
      .where(eq(applications.id, id))
      .returning();
    return updatedApplication;
  }

  async deleteApplication(id: number, userId: string): Promise<boolean> {
    const result = await db
      .delete(applications)
      .where(eq(applications.id, id) && eq(applications.userId, userId));
    return true;
  }

  // Submission operations
  async getUserSubmissions(userId: string): Promise<Submission[]> {
    return await db
      .select()
      .from(submissions)
      .where(eq(submissions.userId, userId))
      .orderBy(desc(submissions.createdAt));
  }

  async getAllSubmissions(): Promise<Submission[]> {
    return await db
      .select()
      .from(submissions)
      .orderBy(desc(submissions.createdAt));
  }

  async createSubmission(submission: InsertSubmission): Promise<Submission> {
    const [newSubmission] = await db
      .insert(submissions)
      .values(submission)
      .returning();
    return newSubmission;
  }
}

export const storage = new DatabaseStorage();