from typing import Annotated
from pydantic import Field
from agent_framework import tool #type: ignore
import json
from typing import Dict, Any
# from yaml_tools.base import github_push_files
from vida.utils.logger import get_logger
from vida.adapters.github.git_search import github_find_folder
from vida.utils.prompt_manager_v2 import GeneratorPrompt
from vida.utils.config import REPO_OWNER,TERRAFORM_MODULES_REPO

logger = get_logger(__name__)



from vida.utils.llm import get_azure_response

def tf_get_azure_response(content, file_name, cloud_provider, resource_group_dict, resource, techstack):
    logger.info("[tf_get_azure_response] Preparing Terraform prompt to generate script.....")
    # print("Inside azure call.....")
    
    # Convert dictionaries to strings for the prompt if needed
    resource_str = json.dumps(resource, indent=2) if isinstance(resource, dict) else str(resource)
    resource_group_str = json.dumps(resource_group_dict, indent=2) if isinstance(resource_group_dict, dict) else str(resource_group_dict)
    text = GeneratorPrompt("terraform-generator")
    text = text.render(content = content, resource_str = resource_str, resource_group_str = resource_group_str, cloud_provider = cloud_provider, file_name = file_name, techstack = techstack)  
    print("="*30 + f"\n prompt to tf_module_builder : {text}\n" + "="*30)
    try:
        response = get_azure_response(text)
        logger.info("[tf_get_azure_response] Azure AI response received.")
        print("[tf_get_azure_response] Azure AI response received.")
        return response
    except Exception as e:
        logger.error(f"[tf_get_azure_response] Azure Error: {str(e)}", exc_info=True)
        print(f"Azure Error: {str(e)}")
        return f"Azure Error: {str(e)}"
    
from vida.adapters.github.git_read import github_read_contents
from vida.utils.prompt_manager_v2 import ToolFieldsPrompt

""""Version 3 - must be refactored"""
_tf_module_builder_feilds = ToolFieldsPrompt("tf-module-builder-field-description")
@tool(name="TF_Module_builder", description="Builds Terraform modules by understanding the requirements such as the desired infrastructure, cloud provider, and specific configurations.", approval_mode="never_require")
async def TF_Module_builder(
    cloud_provider: Annotated[str, Field(description= _tf_module_builder_feilds.get("cloud_provider"))],
    deploy_target_name: Annotated[str, Field(description=_tf_module_builder_feilds.get("deployment_target_name"))],
    target_service_name: Annotated[str, Field(description=_tf_module_builder_feilds.get("target_service_name"))],
    target_service_location: Annotated[str, Field(description=_tf_module_builder_feilds.get("target_service_location"))],
    target_service_sku: Annotated[str, Field(description=_tf_module_builder_feilds.get("target_service_sku"))],
    resource_group_name: Annotated[str, Field(description=_tf_module_builder_feilds.get("resource_group_name"))],
    resource_group_location: Annotated[str, Field(description=_tf_module_builder_feilds.get("resource_group_location"))],
    techstack: Annotated[dict,Field(description=_tf_module_builder_feilds.get("techstack"))],
    repo_name: str = "Shashank-workflow"
):

    Resources = { 
        deploy_target_name: {
            "name" : target_service_name,
            "location": target_service_location,
            "sku": target_service_sku   
        },
        "resource_group": {
            "name": resource_group_name,
            "location": resource_group_location
        }
    }
    logger.info("[terraform_agent][TF_Module_builder] Building Terraform configuration...")
    # print("Building Terraform configuration...")
    logger.info(f"[terraform_agent][TF_Module_builder] Repository Name: {repo_name}")
    logger.info(f"[terraform_agent][TF_Module_builder] Cloud Provider: {cloud_provider}")
    # print("Cloud Provider:", cloud_provider)
    logger.info(f"[terraform_agent][TF_Module_builder] Resources: {Resources}")
    # print("Resources:", Resources)
    # exit(0)

    try:
        # Parse resources if it's a string
        if isinstance(Resources, str):
            resources_dict = json.loads(Resources)
        else:
            resources_dict = Resources

        logger.info(f"[terraform_agent][TF_Module_builder] Parsed Resources Dictionary: {resources_dict}")
        # print("Parsed Resources Dictionary:", resources_dict)

        # Extract resource group information
        resource_group_dict = resources_dict.get("resource_group", {})
        
        # Normalize resource type aliases
        RESOURCE_ALIASES = {
            "app_service": "webapp", "app service": "webapp", "web_app": "webapp", "web app": "webapp",
            "virtual_machine": "vm", "virtual machine": "vm",
        }

        # Get other resources (excluding resource_group)
        other_resources_dict = {
            RESOURCE_ALIASES.get(k.lower(), k.lower()): v
            for k, v in resources_dict.items() if k != "resource_group"
        }

        logger.info(f"[terraform_agent][TF_Module_builder] Resource Group: {resource_group_dict}")
        # print("Resource Group:", resource_group_dict)
        logger.info(f"[terraform_agent][TF_Module_builder] Other Resources: {other_resources_dict}")
        # print("Other Resources:", other_resources_dict)

        # Dictionary to store all files to be pushed
        files_to_push = {}
        processed_resources = []

        # Process each resource type
        for resource_type, resource_config in other_resources_dict.items():
            logger.info(f"[terraform_agent][TF_Module_builder] === Processing {resource_type} ===")
            # print(f"\n=== Processing {resource_type} ===")
            
            # Get all file paths for this resource type
            paths = github_find_folder(cloud_provider, resource_type)
            
            if not paths:
                logger.warning(f"[terraform_agent][TF_Module_builder] No modules found for {resource_type}")
                # print(f"No modules found for {resource_type}")
                continue

            # Process each file for this resource type
            for path in paths:
                try:
                    logger.info(f"[TF_Module_builder] Processing path: {path}")
                    # print(f"Processing path: {path}")
                    
                    # Read file content
                    content = github_read_contents(path)
                    if not content:
                        logger.warning(f"[TF_Module_builder] No content found for {path}")
                        # print(f"No content found for {path}")
                        continue

                    # Extract file information
                    file_name = path.split("/")[-1]  # e.g., "main.tf"
                    
                    logger.info(f"[TF_Module_builder] Processing file: {file_name}")
                    # print(f"Processing file: {file_name}")

                    # Process different file types
                    if file_name == "terraform.tfvars":
                        logger.info(f"[TF_Module_builder] Calling Azure AI for {file_name}")
                        # print(f"Calling Azure AI for {file_name}")
                        
                        try:
                            updated_content = tf_get_azure_response(
                                content=content,
                                file_name=file_name,
                                cloud_provider=cloud_provider,
                                resource_group_dict=resource_group_dict,
                                resource=resource_config,
                                techstack=techstack
                            )
                            logger.info(f"[TF_Module_builder] Azure AI response for {file_name} received : {updated_content}")
                            
                            if updated_content and not updated_content.startswith("Azure Error:"): #type: ignore
                                # Create proper folder structure: repo-name/resource-type/file
                                target_path = f"{repo_name}/{resource_type}/{file_name}"
                                files_to_push[target_path] = updated_content
                                
                                logger.info(f"[TF_Module_builder] Prepared {target_path} for deployment (processed by AI)")
                                # print(f"Prepared {target_path} for deployment (processed by AI)")
                            else:
                                logger.warning(f"[TF_Module_builder] Azure AI returned error for {file_name}: {updated_content}")
                                # print(f"Azure AI returned error for {file_name}: {updated_content}")
                                
                        except Exception as azure_error:
                            logger.error(f"[TF_Module_builder] Error calling Azure AI for {file_name}: {azure_error}", exc_info=True)
                            # print(f"Error calling Azure AI for {file_name}: {azure_error}")
                            continue
                            
                    elif file_name in ["main.tf", "outputs.tf","provider.tf","variables.tf"]:
                        logger.info(f"[TF_Module_builder] Directly pushing {file_name} without AI processing")
                        # print(f"Directly pushing {file_name} without AI processing")
                        
                        # Create proper folder structure: repo-name/resource-type/file
                        target_path = f"{repo_name}/{resource_type}/{file_name}"
                        files_to_push[target_path] = content
                        
                        logger.info(f"[TF_Module_builder] Prepared {target_path} for deployment (direct push)")
                        # print(f"Prepared {target_path} for deployment (direct push)")
                        
                    elif file_name == "README.md":
                        logger.info(f"[TF_Module_builder] Skipping {file_name} as it does not require processing")
                        # print(f"Skipping {file_name} as it does not require processing")
                        
                    else:
                        logger.warning(f"[TF_Module_builder] Skipping file: {file_name} (unknown file type)")
                        # print(f"Skipping file: {file_name} (unknown file type)")

                except Exception as file_error:
                    logger.error(f"[TF_Module_builder] Error processing file {path}: {file_error}", exc_info=True)
                    # print(f"Error processing file {path}: {file_error}")
                    import traceback
                    traceback.print_exc()
                    continue

            processed_resources.append(resource_type)

        # Push all files to the target repository
        if files_to_push:
            logger.info(f"[TF_Module_builder] Pushing {len(files_to_push)} files to repository: {repo_name}")
            print(f"\nPushing {len(files_to_push)} files to repository: {repo_name}")
            
            # Display what will be pushed with proper folder structure
            for file_path in files_to_push.keys():
                logger.info(f"[TF_Module_builder] File to be pushed: {file_path}")
                print(f"  - {file_path}")
            
            try:
                commit_message = f"Add Terraform modules for {', '.join(processed_resources)} on {cloud_provider}"
                github_push_files(
                    repo_name=f"{REPO_OWNER}/{TERRAFORM_MODULES_REPO}",
                    files_to_push=files_to_push,
                    commit_message=commit_message,
                    branch="main"
                )
                
                logger.info(f"[TF_Module_builder] Successfully pushed all files to {repo_name}")
                print(f"Successfully pushed all files to {repo_name}")
                
            except Exception as push_error:
                logger.error(f"[TF_Module_builder] Error pushing files to repository: {push_error}", exc_info=True)
                print(f"Error pushing files to repository: {push_error}")
                return f"ERROR: Failed to push files to repository - {str(push_error)}"
        else:
            logger.info("[TF_Module_builder] No files to push")
            print("No files to push")

        logger.info(f"[TF_Module_builder] TASK COMPLETED: Successfully generated and deployed Terraform configuration for {cloud_provider} with resources: {processed_resources}. Total files pushed to repository {repo_name}: {len(files_to_push)}")
        return f"TASK COMPLETED: Successfully generated and deployed Terraform configuration for {cloud_provider} with resources: {processed_resources}. Total files pushed to repository {repo_name}: {len(files_to_push)}"

    except json.JSONDecodeError as json_error:
        logger.error(f"[TF_Module_builder] JSON parsing error: {json_error}", exc_info=True)
        print(f"JSON parsing error: {json_error}")
        return f"ERROR: Invalid JSON format in Resources parameter - {str(json_error)}"
    
    except Exception as e:
        logger.error(f"[TF_Module_builder] Exception Received: {str(e)}", exc_info=True)
        print("Exception Received:", str(e))
        import traceback
        traceback.print_exc()
        return f"ERROR: Failed to generate Terraform configuration - {str(e)}"