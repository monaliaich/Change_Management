import os
import logging
import argparse
import time
from datetime import datetime as dt
from datetime import timedelta
from typing import Dict, List, Type, Optional
import asyncio

# Import your agents
from agents.identify_change_migration_agent import IdentifyChangeMigrationAgent
from agents.sod_violation_detection_agent import SODViolationDetectionAgent
from agents.approver_validation_agent import ApproverValidationAgent  # Assuming this exists

# Base Agent class (you might already have this)
class BaseAgent:
    def run(self) -> bool:
        raise NotImplementedError("Agent must implement run method")

# Workflow class to define different agent execution sequences
class AuditWorkflow:
    def __init__(self, data_dir: str, output_dir: str):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        self.population_file = None
    
    def run_identify_agent(self) -> bool:
        """Run the identification agent which is common for all workflows"""
        self.logger.info("Starting: Identify Change Migration Population")
        identify_agent = IdentifyChangeMigrationAgent(
            data_dir=self.data_dir, 
            output_data_dir=self.output_dir
        )
        identify_result = identify_agent.run()
        
        if not identify_result:
            self.logger.error("IdentifyChangeMigrationAgent failed.")
            return False
        
        self.population_file = identify_agent.save_verified_population_file()
        self.logger.info(f"Population file created: {self.population_file}")
        return True
    
    def run_sod_workflow(self) -> bool:
        """Run the SOD violation detection workflow"""
        # First run the identify agent
        if not self.run_identify_agent():
            return False
        
        # Then run the SOD agent
        self.logger.info("Starting: SOD Violation Detection")
        sod_agent = SODViolationDetectionAgent(
            data_dir=self.data_dir, 
            output_data_dir=self.output_dir,
            verified_population_file=self.population_file
        )
        sod_result = sod_agent.run()
        
        if not sod_result:
            self.logger.error("SODViolationDetectionAgent failed.")
            return False
        
        self.logger.info("SOD workflow completed successfully")
        return True
    
    def run_approver_validation_workflow(self) -> bool:
        """Run the approver validation workflow"""
        # First run the identify agent
        if not self.run_identify_agent():
            return False
        
        # Then run the approver validation agent
        self.logger.info("Starting: Approver Validation")
        approver_agent = ApproverValidationAgent(
            data_dir=self.data_dir, 
            output_data_dir = os.path.join(self.output_dir),
            verified_population_file=self.population_file
        )

        try:
            # Run the method in the event loop
            approver_result = approver_agent.run()

            if not approver_result:
                self.logger.error("ApproverValidationAgent failed.")
                return False
        
            self.logger.info("Approver validation workflow completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error running ApproverValidationAgent: {str(e)}")
            return False

# Scheduler class (keeping your existing implementation with minor modifications)
class WorkflowScheduler:
    def __init__(self, interval_minutes=5):
        self.interval = interval_minutes
        self.running = False
        self.next_run = None
        self.last_run = None
        self.status = "idle"
        self.logger = logging.getLogger("WorkflowScheduler")
        self.workflow_function = None
    
    def set_interval(self, minutes):
        if minutes < 1:
            self.logger.warning("Interval must be at least 1 minute")
            return False
        self.interval = minutes
        self._update_next_run()
        return True
    
    def _update_next_run(self):
        now = dt.now()
        self.next_run = now + timedelta(minutes=self.interval)
        self.logger.info(f"Next workflow run scheduled for {self.next_run}")
    
    def start(self, workflow_function):
        self.workflow_function = workflow_function
        self.running = True
        self._update_next_run()
        self.status = "running"
        self.logger.info(f"Workflow scheduler started with {self.interval} minute interval")
        return True
    
    def stop(self):
        self.running = False
        self.status = "stopped"
        self.logger.info("Workflow scheduler stopped")
        return True
    
    def get_status(self):
        return {
            "running": self.running,
            "status": self.status,
            "interval": self.interval,
            "last_run": self.last_run.strftime('%Y-%m-%d %H:%M:%S') if self.last_run else None,
            "next_run": self.next_run.strftime('%Y-%m-%d %H:%M:%S') if self.next_run else None
        }
    
    def execute_workflow(self):
        self.status = "executing"
        self.logger.info("Executing workflow")
        
        try:
            # Run the specified workflow function
            success = self.workflow_function()
            
            if success:
                self.logger.info("Workflow execution completed successfully")
            else:
                self.logger.error("Workflow execution failed")
            
            # Update last run time and next run time
            self.last_run = dt.now()
            self._update_next_run()
            
            # Update status
            self.status = "running" if self.running else "stopped"
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error during workflow execution: {str(e)}")
            self.status = "error"
            return False

def setup_logging():
    """Set up logging configuration for the main application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("audit_agents.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("AuditAgents")

def main():
    """Main function to orchestrate the execution of audit agents."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Change Management Audit Automation')
    parser.add_argument('--mode', choices=['run', 'schedule'], default='run',
                      help='Operation mode: run (single execution) or schedule (periodic execution)')
    parser.add_argument('--interval', type=int, default=5,
                      help='Interval in minutes for periodic execution (default: 5)')
    parser.add_argument('--duration', type=int, default=60,
                      help='Duration in minutes to run the scheduler (default: 60, 0 for indefinite)')
    parser.add_argument('--workflow', choices=['sod', 'approver'], default='sod',
                      help='Workflow to execute: sod (SOD Violation) or approver (Approver Validation)')
    args = parser.parse_args()
    
    logger = setup_logging()
    logger.info("Starting Audit Agents workflow")
    
    # Define data directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "input")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "output")
    
    # Create workflow instance
    workflow = AuditWorkflow(data_dir, output_dir)
    
    # Select workflow function based on argument
    if args.workflow == 'sod':
        workflow_function = workflow.run_sod_workflow
        workflow_name = "SOD Violation Detection"
    else:  # approver
        workflow_function = workflow.run_approver_validation_workflow
        workflow_name = "Approver Validation"
    
    logger.info(f"Selected workflow: {workflow_name}")
    
    # Handle different modes
    if args.mode == 'run':
        # Single execution mode
        logger.info("Running in single execution mode")
        success = workflow_function()
        
    elif args.mode == 'schedule':
        # Periodic execution mode
        logger.info(f"Running in periodic execution mode with {args.interval} minute interval")
        
        # Create and start the workflow scheduler
        scheduler = WorkflowScheduler(args.interval)
        scheduler.start(workflow_function)
        
        try:
            # Run for specified duration or indefinitely
            if args.duration > 0:
                logger.info(f"Scheduler will run for {args.duration} minutes")
                end_time = time.time() + (args.duration * 60)
                
                while time.time() < end_time and scheduler.running:
                    now = dt.now()
                    
                    # Check if it's time to run the workflow
                    if scheduler.next_run and now >= scheduler.next_run:
                        scheduler.execute_workflow()
                    
                    # Display status every minute
                    status = scheduler.get_status()
                    logger.info(f"Scheduler status: {status['status']}")
                    if status['next_run']:
                        logger.info(f"Next run at: {status['next_run']}")
                    
                    # Print a simple progress indicator
                    minutes_left = int((end_time - time.time()) / 60)
                    print(f"Scheduler running. {minutes_left} minutes remaining. Press Ctrl+C to stop.", end="\r")
                    
                    # Sleep for a short time to avoid high CPU usage
                    time.sleep(10)
                    
                # Stop the scheduler
                scheduler.stop()
                logger.info("Scheduler stopped after specified duration")
            else:
                logger.info("Scheduler running indefinitely. Press Ctrl+C to stop.")
                
                try:
                    while scheduler.running:
                        now = dt.now()
                        
                        # Check if it's time to run the workflow
                        if scheduler.next_run and now >= scheduler.next_run:
                            scheduler.execute_workflow()
                        
                        # Display status every minute
                        status = scheduler.get_status()
                        logger.info(f"Scheduler status: {status['status']}")
                        if status['next_run']:
                            logger.info(f"Next run at: {status['next_run']}")
                        
                        # Print a simple progress indicator
                        print(f"Scheduler running. Next run at: {status['next_run']}. Press Ctrl+C to stop.", end="\r")
                        
                        # Sleep for a short time to avoid high CPU usage
                        time.sleep(10)
                except KeyboardInterrupt:
                    # Stop the scheduler on Ctrl+C
                    print("\nStopping scheduler...")
                    scheduler.stop()
                    logger.info("Scheduler stopped by user")
        
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            return False
    
    logger.info("Audit Agents workflow completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)