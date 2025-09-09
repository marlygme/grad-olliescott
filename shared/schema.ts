import { sql } from 'drizzle-orm';
import {
  index,
  jsonb,
  pgTable,
  timestamp,
  varchar,
  text,
  integer,
  date,
} from "drizzle-orm/pg-core";

// Session storage table.
// (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
export const sessions = pgTable(
  "sessions",
  {
    sid: varchar("sid").primaryKey(),
    sess: jsonb("sess").notNull(),
    expire: timestamp("expire").notNull(),
  },
  (table) => [index("IDX_session_expire").on(table.expire)],
);

// User storage table.
// (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  email: varchar("email").unique(),
  firstName: varchar("first_name"),
  lastName: varchar("last_name"),
  profileImageUrl: varchar("profile_image_url"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export type UpsertUser = typeof users.$inferInsert;
export type User = typeof users.$inferSelect;

// Job applications table for tracking user applications
export const applications = pgTable("applications", {
  id: integer("id").primaryKey().generatedByDefaultAsIdentity(),
  userId: varchar("user_id").notNull().references(() => users.id),
  company: varchar("company").notNull(),
  role: varchar("role").notNull(),
  applicationDate: date("application_date"),
  university: varchar("university"),
  wam: varchar("wam"),
  status: varchar("status").default("Applied"),
  responseDate: date("response_date"),
  priority: varchar("priority").default("Medium"),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export type Application = typeof applications.$inferSelect;
export type InsertApplication = typeof applications.$inferInsert;

// Experience submissions table for storing user experiences
export const submissions = pgTable("submissions", {
  id: integer("id").primaryKey().generatedByDefaultAsIdentity(),
  userId: varchar("user_id").notNull().references(() => users.id),
  company: varchar("company").notNull(),
  role: varchar("role").notNull(),
  experienceType: varchar("experience_type"),
  theme: varchar("theme"),
  applicationStages: text("application_stages"),
  interviewExperience: text("interview_experience"),
  assessmentCentre: text("assessment_centre"),
  programStructure: text("program_structure"),
  salaryBenefits: text("salary_benefits"),
  cultureEnvironment: text("culture_environment"),
  hoursWorkload: text("hours_workload"),
  practiceAreas: text("practice_areas"),
  generalExperience: text("general_experience"),
  proTip: text("pro_tip"),
  advice: text("advice"),
  createdAt: timestamp("created_at").defaultNow(),
});

export type Submission = typeof submissions.$inferSelect;
export type InsertSubmission = typeof submissions.$inferInsert;