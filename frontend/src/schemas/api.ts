import { z } from "zod";

export const DashboardApiErrorDetailSchema = z.object({
  code: z.string(),
  message: z.string(),
});

export const DashboardApiErrorSchema = z.object({
  error: DashboardApiErrorDetailSchema,
});

export const ApiErrorDetailSchema = z.object({
  message: z.string().optional(),
  type: z.string().optional(),
  code: z.string().optional(),
  param: z.string().optional(),
});

export const ApiErrorSchema = z.object({
  error: ApiErrorDetailSchema,
});

export const ApiErrorResponseSchema = z.union([
  DashboardApiErrorSchema,
  ApiErrorSchema,
]);

export type DashboardApiError = z.infer<typeof DashboardApiErrorSchema>;
export type ApiError = z.infer<typeof ApiErrorSchema>;
export type ApiErrorResponse = z.infer<typeof ApiErrorResponseSchema>;
