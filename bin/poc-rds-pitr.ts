#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "@aws-cdk/core";
import {
  PocRdsPitrStack,
  PocRdsPitrStackProps,
} from "../lib/poc-rds-pitr-stack";
require("dotenv").config();

const app = new cdk.App();
new PocRdsPitrStack(app, "PocRdsPitrStack", {
  trustedDbIngress: process.env.TRUSTED_INGRESS_DB_CIDR,
} as PocRdsPitrStackProps);
